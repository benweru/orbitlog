"""Implemented fault classes. These run the payload app as a subprocess in a
temp work dir, so they never touch the real disk beyond small files.

Not implemented yet (raise NotImplementedError via get_injector): every other
class in configs/fault_classes.yaml.
"""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

from orbitlog.faults.injector import FaultInjector, register
from orbitlog.payload import make_frame


class _PayloadInjector(FaultInjector):
    component = "payload.imgproc"

    def setup(self) -> None:
        rng = random.Random(self.seed)
        w, h = self.params["width"], self.params["height"]
        self.input = self.workdir / "frame.olim"
        self.input.write_bytes(make_frame(w, h, rng.randbytes(w * h)))
        self.output = self.workdir / "out.olim"
        self.log = self.workdir / "payload.log"

    @staticmethod
    def _size(rng: random.Random) -> dict:
        return {"width": rng.choice([16, 32, 64]), "height": rng.choice([16, 32, 64])}

    def payload_args(self) -> list[str]:
        return []

    def trigger(self) -> None:
        env = dict(os.environ)
        src = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
        cmd = [sys.executable, "-m", "orbitlog.payload", "--input", str(self.input),
               "--output", str(self.output), "--log", str(self.log), *self.payload_args()]
        self.proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        if self.proc.returncode == 0:
            raise RuntimeError("payload exited 0: fault did not manifest")

    def collect(self, out_dir: Path) -> list[str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "stderr.txt").write_text(self.proc.stderr)
        (out_dir / "stdout.txt").write_text(self.proc.stdout)
        (out_dir / "exit_code.txt").write_text(f"{self.proc.returncode}\n")
        if self.log.exists():
            shutil.copy(self.log, out_dir / "payload.log")
        return sorted(p.name for p in out_dir.iterdir())


@register("disk_full")
class DiskFull(_PayloadInjector):
    """Payload output path points at /dev/full, which returns a real ENOSPC on
    write. Nothing fills a real disk. Linux only.
    TODO: size-limited loop/tmpfs variant (needs privileges, e.g. in Docker).
    """
    component = "payload.storage"

    def choose_params(self, rng):
        return {**self._size(rng), "method": "dev_full"}

    def setup(self) -> None:
        super().setup()
        if not os.path.exists("/dev/full"):
            raise RuntimeError("/dev/full not available on this platform")
        self.output = Path("/dev/full")


@register("payload_python_exception")
class PayloadPythonException(_PayloadInjector):
    """A seeded bug at one processing stage raises a real Python exception."""

    def choose_params(self, rng):
        return {**self._size(rng), "stage": rng.choice(["invert", "stats", "metadata"])}

    def payload_args(self):
        return ["--fault-stage", self.params["stage"]]


@register("corrupt_input_file")
class CorruptInputFile(_PayloadInjector):
    """Input frame is truncated or has bit flips, chosen from the seed."""

    def choose_params(self, rng):
        p = {**self._size(rng), "mode": rng.choice(["truncate", "bitflip", "bad_magic"])}
        n = p["width"] * p["height"] + 12
        if p["mode"] == "truncate":
            p["keep_bytes"] = rng.randrange(4, n - 1)
        elif p["mode"] == "bitflip":
            p["offsets"] = sorted(rng.sample(range(12, n), rng.randint(1, 4)))
        return p

    def setup(self) -> None:
        super().setup()
        data = bytearray(self.input.read_bytes())
        mode = self.params["mode"]
        if mode == "truncate":
            data = data[: self.params["keep_bytes"]]
        elif mode == "bitflip":
            for off in self.params["offsets"]:
                data[off] ^= 0x01
        else:
            data[0:4] = b"XXXX"
        self.input.write_bytes(bytes(data))
