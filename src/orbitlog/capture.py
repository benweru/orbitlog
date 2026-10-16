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
# optionally prefixed by a docker --timestamps RFC3339 stamp.
EVS_RE = re.compile(
    r"^(?:(?P<docker_ts>\d{4}-\d{2}-\d{2}T\S+Z)\s+)?"
    r"EVS Port(?P<port>\d+)\s+(?P<cfs_time>\d{4}-\d{3}-\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(?P<scid>\d+)/(?P<cpu>\d+)/(?P<app>[A-Za-z0-9_]+)\s+(?P<eid>\d+):\s?(?P<text>.*)$"
)


def parse_evs_line(line: str) -> dict | None:
    """Parse one EVS port line. The port output carries no event type, so none is returned."""
    m = EVS_RE.match(line.rstrip("\r\n"))
    if not m:
        return None
    d = m.groupdict()
    return {
        "docker_ts": d["docker_ts"],
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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def container_running(name: str = DEFAULT_CONTAINER) -> bool:
    if shutil.which("docker") is None:
        return False
    r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


class ContainerLogCapture:
    """Context manager: records the UTC window and saves `docker logs` for it.

    After exit, `status` is "captured", "unavailable" (no docker/container) or
    "error" (docker logs failed), and `files` lists what was written.
    """

    def __init__(self, artefact_dir: str | Path, name: str = DEFAULT_CONTAINER):
        self.dir = Path(artefact_dir)
        self.name = name
        self.status = "unavailable"
        self.start = self.end = None
        self.files: list[str] = []
        self.error: str | None = None

    def __enter__(self):
        self.start = _now()
        return self

    def __exit__(self, *exc):
        self.end = _now()
        if not container_running(self.name):
            self.status = "unavailable"
            return False
        r = subprocess.run(
            ["docker", "logs", "--timestamps", "--since", self.start, "--until", self.end, self.name],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            self.status, self.error = "error", r.stderr.strip()[:500]
            return False
        self.dir.mkdir(parents=True, exist_ok=True)
        text = r.stdout + r.stderr  # cFS writes to both streams
        (self.dir / "container.log").write_text(text)
        with open(self.dir / "evs.jsonl", "w", encoding="utf-8") as f:
            for e in parse_evs(text):
                f.write(json.dumps(e, sort_keys=True) + "\n")
        self.files = ["container.log", "evs.jsonl"]
        self.status = "captured"
        return False

    def meta(self) -> dict:
        m = {"capture": self.status, "capture_start": self.start, "capture_end": self.end,
             "container": self.name}
        if self.error:
            m["capture_error"] = self.error
        return m
