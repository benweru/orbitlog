"""Faults that only exist inside the running cFS container.

Each inject() writes label.json before trigger(). trigger() raises if the
expected EVS line never appears, and the label stays trigger_status failed.
"""
from __future__ import annotations

import random
import time
from pathlib import Path

from orbitlog.cfs.cmd import (
    SAMPLE_PIPE_DEPTH,
    TABLE_NAME,
    fault_app_exit_cmd,
    load_table_cmd,
    restart_app_cmd,
    send_udp,
    validate_table_cmd,
)
from orbitlog.cfs.container import CfsContainer
from orbitlog.faults.injector import FaultInjector, register

# Baked by docker/cfs/Dockerfile. Int1 is above the sample_app maximum of 10.
BAD_TABLES = (
    (11, "/cf/b11.tbl"),
    (42, "/cf/b42.tbl"),
    (100, "/cf/b100.tbl"),
    (1000, "/cf/b1000.tbl"),
)


class _CfsFault(FaultInjector):
    def __init__(self, workdir: Path):
        super().__init__(workdir)
        self.container: CfsContainer | None = None

    def _boot(self) -> CfsContainer:
        name = f"orbitlog-cfs-{self.fault_class}-{self.seed}"
        box = CfsContainer(name)
        self.container = box
        box.start()
        if not box.is_operational():
            raise RuntimeError("cFS did not reach OPERATIONAL")
        if box.port is None:
            raise RuntimeError("ci_lab UDP port was not published")
        return box

    def _send(self, box: CfsContainer, packet: bytes, times: int = 1) -> None:
        assert box.port is not None
        for _ in range(times):
            send_udp(box.host, box.port, packet)

    def collect(self, out_dir: Path) -> list[str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        if self.container is None:
            return []
        text = self.container.logs()
        (out_dir / "container.log").write_text(text, encoding="utf-8")
        return ["container.log"]

    def cleanup(self) -> None:
        if self.container is not None:
            self.container.stop()
            self.container = None


@register("table_load_validation")
class TableLoadValidation(_CfsFault):
    component = "cfs.tbl.sample_app"

    def choose_params(self, rng: random.Random) -> dict:
        int1, filename = rng.choice(BAD_TABLES)
        return {"Int1": int1, "filename": filename, "table": TABLE_NAME}

    def trigger(self) -> None:
        box = self._boot()
        self._send(box, load_table_cmd(self.params["filename"]))
        time.sleep(0.5)
        self._send(box, validate_table_cmd())
        box.wait_for("validation failed for")


@register("sb_pipe_full")
class SbPipeFull(_CfsFault):
    """SAMPLE_APP NOOP burst.

    The command pipe depth is 32. sample_app drains every queued command each
    time it is scheduled, and stock ci_lab ingests only 11 packets per wakeup,
    so a burst just above 32 never overflows. The image raises
    CI_LAB_PLATFORM_MAX_INGEST_PKTS to 64. ci_lab priority (40) is higher than
    sample_app (50), so one wakeup can enqueue more than 32 commands before
    sample_app runs. The seeded count is 40 to 64, sent by /opt/orbitlog/burst
    to 127.0.0.1:1234. On this machine sample_app still drains the pipe in
    time, so trigger() raises and the label stays failed. It does not write
    a Pipe Overflow line.
    """

    component = "cfs.sb.sample_app"

    def choose_params(self, rng: random.Random) -> dict:
        return {
            "pipe_depth": SAMPLE_PIPE_DEPTH,
            "noop_count": 40 + rng.randrange(0, 25),
            "msg": "SAMPLE_APP NOOP",
        }

    def trigger(self) -> None:
        box = self._boot()
        # Host UDP was not enough. /opt/orbitlog/burst sends to 127.0.0.1:1234.
        # sample_app still drains the pipe before it reaches depth 32.
        box.exec("/opt/orbitlog/burst", str(self.params["noop_count"]))
        try:
            box.wait_for("Pipe Overflow", timeout_s=8)
        except RuntimeError:
            log = box.logs()
            raise RuntimeError(
                "no Pipe Overflow after "
                f"{self.params['noop_count']} NOOPs; "
                f"log has {log.count('NOOP command')} NOOP lines and "
                f"{log.count('Pipe Overflow')} overflow lines"
            )


@register("cfs_app_crash_restart")
class CfsAppCrashRestart(_CfsFault):
    """fault_app error-exits, and ES is told to restart it.

    HS was not used. Its default app-monitor table only watches cFE core apps
    and every action is NOACT, and SAMPLE_APP has no command that stops it
    checking in. fault_app (docker/cfs/fault_app.c) is option (c): EXIT command
    calls CFE_ES_ExitApp(APP_ERROR), which emits the ERREXIT event.

    CFE_ES_RestartAppCmd only works while the app is still registered, so the
    injector sends the restart first (option b) and the error exit second.
    Both events are required. A missing line fails the trigger.
    """

    component = "cfs.es.fault_app"

    def choose_params(self, rng: random.Random) -> dict:
        return {"app": "FAULT_APP", "exit_cc": 1, "order": "restart_then_error_exit"}

    def trigger(self) -> None:
        box = self._boot()
        box.wait_for("FAULT_APP initialized")
        self._send(box, restart_app_cmd("FAULT_APP"))
        # "Initiated" is logged before the restart finishes. The exit command
        # is dropped if it arrives while FAULT_APP is not subscribed yet.
        box.wait_for("Restart Application FAULT_APP Completed")
        self._send(box, fault_app_exit_cmd())
        box.wait_for("Exit Application FAULT_APP")
