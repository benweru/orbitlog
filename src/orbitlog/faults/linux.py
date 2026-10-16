"""Linux-side faults from Satlyt's Gemma case study
(https://deepmind.google/models/gemma/gemmaverse/satlyt/). Brief:
docs/tasks/week3-linux-faults.md.

oom_alloc_failure runs in a cgroup v2-capped container, so it works anywhere
Docker runs. i2c_sensor_nack needs a Linux host with root and the i2c-stub
module; elsewhere its trigger raises and the label stays failed.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from orbitlog.faults.injector import FaultInjector, register

# python:3.13-slim, digest pulled 16 Oct 2026.
OOM_IMAGE = "python@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f"
OOM_LOADER = Path(__file__).with_name("oom_loader.py")
# (width, height, channels). 12000x12000x1 is the article's 144000000-byte frame.
OOM_FRAMES = ((12000, 12000, 1), (8000, 8000, 3), (16000, 9000, 1), (10000, 10000, 3))
OOM_CAPS_MIB = (64, 96, 128)
OOM_MODES = ("rlimit_as", "cgroup_oom_kill")

# 0x36 is the address in the article; the others are common camera-sensor addresses.
I2C_SENSOR_ADDRS = (0x36, 0x10, 0x1A, 0x3C)
I2C_DECOY_ADDRS = (0x50, 0x48)
I2C_REGS = (0x00, 0x0A, 0x30)
I2C_STUB_NAME = "SMBus stub driver"


@register("oom_alloc_failure")
class OomAllocFailure(FaultInjector):
    """Frame preprocessing allocates more than the memory cap allows.

    rlimit_as: `ulimit -v` at the cap, so bytearray() raises MemoryError.
    cgroup_oom_kill: the page-touching allocation hits memory.max (swap off)
    and the kernel OOM killer ends python with SIGKILL (exit 137).
    """

    component = "payload.preprocess"

    def choose_params(self, rng):
        w, h, c = rng.choice(OOM_FRAMES)
        return {"width": w, "height": h, "channels": c, "frame_bytes": w * h * c,
                "cap_mib": rng.choice(OOM_CAPS_MIB), "mode": rng.choice(OOM_MODES)}

    def _script(self) -> str:
        p = self.params
        limit = f"ulimit -v {p['cap_mib'] * 1024}; " if p["mode"] == "rlimit_as" else ""
        return (f"cat > /tmp/oom_loader.py; {limit}"
                f"python /tmp/oom_loader.py {p['width']} {p['height']} {p['channels']}; "
                "echo python_exit=$?; "
                "echo '--- memory.events'; cat /sys/fs/cgroup/memory.events; "
                "echo memory.peak=$(cat /sys/fs/cgroup/memory.peak); "
                "echo memory.max=$(cat /sys/fs/cgroup/memory.max)")

    def docker_cmd(self) -> list[str]:
        cap = f"{self.params['cap_mib']}m"
        return ["docker", "run", "--rm", "-i", "--name", f"orbitlog-oom-{self.seed}-{os.getpid()}",
                f"--memory={cap}", f"--memory-swap={cap}", OOM_IMAGE, "sh", "-c", self._script()]

    def trigger(self) -> None:
        if shutil.which("docker") is None:
            raise RuntimeError("docker not found")
        self.proc = subprocess.run(self.docker_cmd(), input=OOM_LOADER.read_text(encoding="utf-8"),
                                   capture_output=True, text=True, timeout=180)
        out, err = self.proc.stdout, self.proc.stderr
        m = re.search(r"^python_exit=(\d+)$", out, re.M)
        kills = re.search(r"^oom_kill (\d+)$", out, re.M)
        py_exit = int(m.group(1)) if m else None
        oom_kill = int(kills.group(1)) if kills else None
        if "preprocess: loading" not in out:
            raise RuntimeError(f"loader never started (docker exit {self.proc.returncode}): {err.strip()[-300:]}")
        if self.params["mode"] == "rlimit_as":
            if py_exit != 1 or "MemoryError" not in err:
                raise RuntimeError(f"no MemoryError: python_exit={py_exit}")
        elif py_exit != 137 or not oom_kill:
            raise RuntimeError(f"no OOM kill: python_exit={py_exit}, oom_kill={oom_kill}")

    def collect(self, out_dir: Path) -> list[str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        if getattr(self, "proc", None) is None:
            return []
        (out_dir / "stdout.txt").write_text(self.proc.stdout, encoding="utf-8")
        (out_dir / "stderr.txt").write_text(self.proc.stderr, encoding="utf-8")
        return ["stderr.txt", "stdout.txt"]


def _dmesg() -> list[str]:
    r = subprocess.run(["dmesg"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def find_stub_bus(sys_class: Path = Path("/sys/class/i2c-dev")) -> int | None:
    for name_file in sorted(sys_class.glob("i2c-*/name")):
        if name_file.read_text().strip() == I2C_STUB_NAME:
            return int(name_file.parent.name.split("-")[1])
    return None


@register("i2c_sensor_nack")
class I2cSensorNack(FaultInjector):
    """A camera capture reads a sensor address with no device behind it.

    i2c-stub emulates chips only at chip_addr (a decoy here), so the SMBus
    read at the sensor address is not acknowledged and the kernel returns an
    error to the capture process. The errno is recorded as it occurs; the
    article's Errno 121 came from the tegra-i2c driver and may differ.
    """

    component = "payload.camera"

    def __init__(self, workdir: Path):
        super().__init__(workdir)
        self.loaded_stub = False
        self.proc: subprocess.CompletedProcess | None = None
        self.dmesg_window: list[str] = []

    def choose_params(self, rng):
        return {"sensor_addr": f"0x{rng.choice(I2C_SENSOR_ADDRS):02x}",
                "decoy_addr": f"0x{rng.choice(I2C_DECOY_ADDRS):02x}",
                "reg": f"0x{rng.choice(I2C_REGS):02x}", "method": "i2c_stub"}

    def _check_host(self) -> None:
        if not sys.platform.startswith("linux"):
            raise RuntimeError(f"i2c-stub needs a Linux host, not {sys.platform}")
        if os.geteuid() != 0:
            raise RuntimeError("loading i2c-stub needs root")
        if shutil.which("modprobe") is None:
            raise RuntimeError("modprobe not found")
        if Path("/sys/module/i2c_stub").exists():
            raise RuntimeError("i2c-stub is already loaded; refusing to reconfigure it")

    def _modprobe(self, *args: str) -> None:
        r = subprocess.run(["modprobe", *args], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"modprobe {' '.join(args)} failed: {r.stderr.strip()}")

    def trigger(self) -> None:
        self._check_host()
        before = len(_dmesg())
        self._modprobe("i2c-dev")
        self._modprobe("i2c-stub", f"chip_addr={self.params['decoy_addr']}")
        self.loaded_stub = True
        bus = find_stub_bus()
        if bus is None:
            raise RuntimeError("i2c-stub loaded but no /dev/i2c-N named 'SMBus stub driver'")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + env.get("PYTHONPATH", "")
        self.proc = subprocess.run(
            [sys.executable, "-m", "orbitlog.faults.i2c_capture", "--bus", str(bus),
             "--addr", self.params["sensor_addr"], "--reg", self.params["reg"]],
            capture_output=True, text=True, env=env, timeout=30)
        self.dmesg_window = _dmesg()[before:]
        if self.proc.returncode == 0 or "OSError" not in self.proc.stderr:
            raise RuntimeError(f"sensor read did not fail: exit {self.proc.returncode}")

    def collect(self, out_dir: Path) -> list[str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        if self.proc is None:
            return []
        (out_dir / "stdout.txt").write_text(self.proc.stdout, encoding="utf-8")
        (out_dir / "stderr.txt").write_text(self.proc.stderr, encoding="utf-8")
        (out_dir / "dmesg.txt").write_text("".join(f"{l}\n" for l in self.dmesg_window), encoding="utf-8")
        return ["dmesg.txt", "stderr.txt", "stdout.txt"]

    def cleanup(self) -> None:
        if self.loaded_stub:
            subprocess.run(["modprobe", "-r", "i2c-stub"], capture_output=True, text=True)
            self.loaded_stub = False
