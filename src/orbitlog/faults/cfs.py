"""Faults that only exist inside the running cFS container.

Each inject() writes label.json before trigger(). trigger() raises if the
expected EVS event (matched on app name and event ID) never appears, and the
label stays trigger_status failed. Pass keep_container_log as inject()'s
before_cleanup to keep the container log of a failed trigger.
"""
from __future__ import annotations

import random
from pathlib import Path

from orbitlog.cfs.cmd import (
    SLOW_APP_CMD_MID,
    SLOW_APP_PIPE_DEPTH,
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

# cFE v7.0.1 event IDs (cfe_*_eventids.h in the image).
CFE_TBL_FILE_LOADED_INF_EID = 12
CFE_TBL_VALIDATION_ERR_EID = 96
CFE_ES_RESTART_APP_INF_EID = 10
CFE_ES_ERREXIT_APP_INF_EID = 14
CFE_SB_Q_FULL_ERR_EID = 25
APP_INIT_EID = 1  # fault_app.c and slow_app.c


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


def keep_container_log(injector, out_dir: Path) -> None:
    """before_cleanup hook: save container.log when collect() did not run."""
    if not isinstance(injector, _CfsFault) or injector.container is None:
        return
    if (Path(out_dir) / "artefacts" / "container.log").exists():
        return
    injector.collect(Path(out_dir) / "artefacts")


@register("table_load_validation")
class TableLoadValidation(_CfsFault):
    component = "cfs.tbl.sample_app"

    def choose_params(self, rng: random.Random) -> dict:
        int1, filename = rng.choice(BAD_TABLES)
        return {"Int1": int1, "filename": filename, "table": TABLE_NAME}

    def trigger(self) -> None:
        box = self._boot()
        self._send(box, load_table_cmd(self.params["filename"]))
        box.wait_for_event("CFE_TBL", CFE_TBL_FILE_LOADED_INF_EID, timeout_s=10, subject=self.params["filename"])
        self._send(box, validate_table_cmd())
        box.wait_for_event("CFE_TBL", CFE_TBL_VALIDATION_ERR_EID, subject=TABLE_NAME)


@register("sb_pipe_full")
class SbPipeFull(_CfsFault):
    """Burst of commands into SLOW_APP's depth-4 pipe.

    sample_app drains its depth-32 pipe faster than ci_lab can fill it, so
    bursts at it never overflowed. slow_app (docker/cfs/slow_app.c) drains
    its pipe only once every 5 s. The burst is sent in-container by
    /opt/orbitlog/burst and is at least 2 * depth + 1 commands, so even if a
    drain lands mid-burst one side still exceeds the depth. Success is the
    CFE_SB Pipe Overflow event (ID 25) naming SLOW_APP's pipe.
    """

    component = "cfs.sb.slow_app"

    def choose_params(self, rng: random.Random) -> dict:
        return {
            "pipe_depth": SLOW_APP_PIPE_DEPTH,
            "burst_count": 2 * SLOW_APP_PIPE_DEPTH + 1 + rng.randrange(0, 32),
            "msg_id": f"0x{SLOW_APP_CMD_MID:04X}",
        }

    def trigger(self) -> None:
        box = self._boot()
        box.wait_for_event("SLOW_APP", APP_INIT_EID)
        box.exec("/opt/orbitlog/burst", str(self.params["burst_count"]), self.params["msg_id"][2:])
        box.wait_for_event("CFE_SB", CFE_SB_Q_FULL_ERR_EID, timeout_s=10, subject="pipe SLOW_APP_CMD")


@register("cfs_app_crash_restart")
class CfsAppCrashRestart(_CfsFault):
    """fault_app error-exits, and ES is told to restart it.

    HS was not used. Its default app-monitor table only watches cFE core apps
    and every action is NOACT, and SAMPLE_APP has no command that stops it
    checking in. fault_app (docker/cfs/fault_app.c) is option (c): EXIT command
    calls CFE_ES_ExitApp(APP_ERROR), which emits the ERREXIT event.

    CFE_ES_RestartAppCmd only works while the app is still registered, so the
    injector sends the restart first (option b) and the error exit second.
    Both events are required. A missing event fails the trigger.
    """

    component = "cfs.es.fault_app"

    def choose_params(self, rng: random.Random) -> dict:
        return {"app": "FAULT_APP", "exit_cc": 1, "order": "restart_then_error_exit"}

    def trigger(self) -> None:
        box = self._boot()
        box.wait_for_event("FAULT_APP", APP_INIT_EID)
        self._send(box, restart_app_cmd("FAULT_APP"))
        # ES event 10 ("Restart Application ... Completed") is logged once
        # FAULT_APP is re-created. The exit command is dropped if it arrives
        # while FAULT_APP is not subscribed yet.
        box.wait_for_event("CFE_ES", CFE_ES_RESTART_APP_INF_EID, subject="FAULT_APP")
        self._send(box, fault_app_exit_cmd())
        box.wait_for_event("CFE_ES", CFE_ES_ERREXIT_APP_INF_EID, subject="FAULT_APP")
