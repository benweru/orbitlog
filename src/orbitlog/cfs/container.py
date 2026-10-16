"""Start and stop one orbitlog-cfs container per fault case."""
from __future__ import annotations

import subprocess
import time

from orbitlog.capture import parse_evs

IMAGE = "orbitlog-cfs"
OPERATIONAL = "CFE_ES_Main entering OPERATIONAL"


class CfsContainer:
    def __init__(self, name: str):
        self.name = name
        self.host = "127.0.0.1"
        self.port: int | None = None

    def start(self) -> None:
        subprocess.run(
            [
                "docker", "run", "-d", "--name", self.name, "--rm",
                "--ulimit", "msgqueue=819200",
                "--sysctl", "fs.mqueue.msg_max=256",
                "--sysctl", "fs.mqueue.msgsize_max=16384",
                "-p", "127.0.0.1::1234/udp",
                IMAGE,
            ],
            check=True, capture_output=True, text=True,
        )
        mapped = subprocess.run(
            ["docker", "port", self.name, "1234/udp"],
            check=True, capture_output=True, text=True,
        )
        line = mapped.stdout.strip().splitlines()[0]
        self.port = int(line.rsplit(":", 1)[1])

    def logs(self) -> str:
        result = subprocess.run(
            ["docker", "logs", self.name],
            check=True, capture_output=True, text=True, errors="replace",
        )
        return result.stdout + result.stderr

    def is_operational(self, timeout_s: float = 90) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                if OPERATIONAL in self.logs():
                    return True
            except subprocess.CalledProcessError:
                pass
            time.sleep(0.5)
        return False

    def wait_for(self, text: str, timeout_s: float = 20) -> str:
        deadline = time.monotonic() + timeout_s
        last = ""
        while time.monotonic() < deadline:
            last = self.logs()
            if text in last:
                return last
            time.sleep(0.25)
        raise RuntimeError(f"timed out waiting for {text!r} in {self.name}")

    def wait_for_event(self, app: str, event_id: int, timeout_s: float = 20, subject: str | None = None) -> dict:
        """Wait for an EVS event from `app` with `event_id` and return it parsed.

        `subject`, if given, must appear in the event text. cFS reuses event IDs
        for every app it acts on (boot logs CFE_ES 14 for SBN, for example).
        """
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            for event in parse_evs(self.logs()):
                if (event["app"] == app and event["event_id"] == event_id
                        and (subject is None or subject in event["text"])):
                    return event
            time.sleep(0.25)
        about = f" about {subject!r}" if subject else ""
        raise RuntimeError(f"timed out after {timeout_s}s waiting for {app} event {event_id}{about} in {self.name}")

    def exec(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", "exec", self.name, *args],
            check=True, capture_output=True, text=True,
        )

    def stop(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, text=True)
        self.port = None
