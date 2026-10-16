"""Capture cFS container logs and EVS events for one fault window.

Never writes synthetic log content: if Docker or the container is not
available, nothing is written and the status says so.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CONTAINER = "orbitlog-cfs"

# e.g. "EVS Port1 1980-012-14:03:20.05160 66/1/CFE_ES 1: cFE ES Initialized: ..."
# The EVS text can appear mid-line: other apps print progress characters
# without a newline (a real CFE_TBL 96 line arrived as ".EVS Port1 ..."), so
# the event is searched for anywhere. An optional docker --timestamps stamp
# is taken from the start of the line.
DOCKER_TS_RE = re.compile(r"^(?P<docker_ts>\d{4}-\d{2}-\d{2}T\S+Z)\s")
EVS_RE = re.compile(
    r"EVS Port(?P<port>\d+)\s+(?P<cfs_time>\d{4}-\d{3}-\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(?P<scid>\d+)/(?P<cpu>\d+)/(?P<app>[A-Za-z0-9_]+)\s+(?P<eid>\d+):\s?(?P<text>.*)$"
)


def parse_evs_line(line: str) -> dict | None:
    """Parse one EVS port line. The port output carries no event type, so none is returned."""
    line = line.rstrip("\r\n")
    ts = DOCKER_TS_RE.match(line)
    m = EVS_RE.search(line)
    if not m:
        return None
    d = m.groupdict()
    return {
        "docker_ts": ts["docker_ts"] if ts else None,
        "cfs_time": d["cfs_time"],
        "port": int(d["port"]),
        "scid": int(d["scid"]),
        "cpu": int(d["cpu"]),
        "app": d["app"],
        "event_id": int(d["eid"]),
        "text": d["text"],
    }


def parse_evs(text: str) -> list[dict]:
    return [e for e in map(parse_evs_line, text.splitlines()) if e]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def container_running(name: str = DEFAULT_CONTAINER) -> bool:
    if shutil.which("docker") is None:
        return False
    r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


CAPTURE_LOG = "capture_container.log"  # distinct from injectors' own container.log
EVS_FILE = "evs.jsonl"


def case_container_name(injector) -> str | None:
    """Name of a container the injector started for this case, if any.

    Duck-typed on `injector.container.name` (what the cFS injectors set), so
    no change to their code is needed.
    """
    c = getattr(injector, "container", None)
    name = getattr(c, "name", None)
    return name if isinstance(name, str) and name else None


def _docker_logs(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "logs", "--timestamps", *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def capture(injector, artefact_dir: str | Path, window_start: str,
            shared_name: str = DEFAULT_CONTAINER) -> dict:
    """Save container logs for one case. Call before the injector's cleanup().

    - The case has its own container: save its full log.
    - Otherwise, if the shared container is running: save the window
      [window_start, now].
    - Otherwise: write nothing, return capture "unavailable".
    Writes CAPTURE_LOG and EVS_FILE only; never touches other artefacts.
    """
    adir = Path(artefact_dir)
    end = now_utc()
    meta = {"capture": "unavailable", "capture_start": window_start, "capture_end": end,
            "capture_source": None, "container": None}
    own = case_container_name(injector)
    if own and shutil.which("docker"):
        meta.update(capture_source="case_container", container=own)
        r = _docker_logs([own])
    elif container_running(shared_name):
        meta.update(capture_source="shared_container", container=shared_name)
        r = _docker_logs(["--since", window_start, "--until", end, shared_name])
    else:
        return meta
    if r.returncode != 0:
        meta.update(capture="error", capture_error=(r.stderr or "").strip()[:500])
        return meta
    text = (r.stdout or "") + (r.stderr or "")  # cFS writes to both streams
    adir.mkdir(parents=True, exist_ok=True)
    (adir / CAPTURE_LOG).write_text(text, encoding="utf-8")
    with open(adir / EVS_FILE, "w", encoding="utf-8") as f:
        for e in parse_evs(text):
            f.write(json.dumps(e, sort_keys=True) + "\n")
    meta["capture"] = "captured"
    return meta
