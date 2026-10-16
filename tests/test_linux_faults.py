import random
import subprocess
import sys

import pytest

from orbitlog.dataset import load_label, validate_label
from orbitlog.faults import linux
from orbitlog.faults.injector import inject


def test_oom_params_always_exceed_cap():
    for s in range(200):
        p = linux.OomAllocFailure.__new__(linux.OomAllocFailure).choose_params(random.Random(s))
        assert p["frame_bytes"] > p["cap_mib"] * 2**20
        assert p["mode"] in linux.OOM_MODES


def test_oom_docker_cmd_caps_memory_and_swap(tmp_path):
    inj = linux.OomAllocFailure(tmp_path)
    p = inj.prepare(3)
    cmd = inj.docker_cmd()
    assert f"--memory={p['cap_mib']}m" in cmd and f"--memory-swap={p['cap_mib']}m" in cmd
    assert linux.OOM_IMAGE in cmd and linux.OOM_IMAGE.startswith("python@sha256:")
    assert ("ulimit -v" in cmd[-1]) == (p["mode"] == "rlimit_as")


def _fake_run(tmp_path, stdout, stderr, seen):
    def run(cmd, **kw):
        seen.append(load_label(tmp_path / "label.json")["trigger_status"])
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr=stderr)
    return run


def test_oom_label_written_before_trigger_and_failure_kept(tmp_path, monkeypatch):
    # Docker output that shows no OOM: the trigger must fail, not be relabelled.
    seen = []
    monkeypatch.setattr(linux.shutil, "which", lambda x: "docker")
    monkeypatch.setattr(linux.subprocess, "run",
                        _fake_run(tmp_path, "preprocess: loading 1x1x1 frame (1 bytes)\npython_exit=0\noom_kill 0\n", "", seen))
    label = inject("oom_alloc_failure", 0, tmp_path)
    assert seen == ["pending"]
    assert label["trigger_status"] == "failed"
    validate_label(load_label(tmp_path / "label.json"))


def test_oom_without_docker_fails_cleanly(tmp_path, monkeypatch):
    monkeypatch.setattr(linux.shutil, "which", lambda x: None)
    label = inject("oom_alloc_failure", 0, tmp_path)
    assert label["trigger_status"] == "failed" and "docker not found" in label["trigger_error"]


def test_i2c_params_deterministic_and_include_article_address():
    ps = [linux.I2cSensorNack.__new__(linux.I2cSensorNack).choose_params(random.Random(s)) for s in range(50)]
    assert ps[7] == linux.I2cSensorNack.__new__(linux.I2cSensorNack).choose_params(random.Random(7))
    assert "0x36" in {p["sensor_addr"] for p in ps}
    assert all(p["sensor_addr"] != p["decoy_addr"] for p in ps)


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="checks the non-Linux path")
def test_i2c_non_linux_records_failed(tmp_path):
    label = inject("i2c_sensor_nack", 0, tmp_path)
    assert label["trigger_status"] == "failed"
    assert "needs a Linux host" in label["trigger_error"]
    assert load_label(tmp_path / "label.json")["trigger_status"] == "failed"


def test_find_stub_bus(tmp_path):
    for n, name in ((0, "Synopsys DesignWare I2C adapter"), (3, linux.I2C_STUB_NAME)):
        d = tmp_path / f"i2c-{n}"
        d.mkdir()
        (d / "name").write_text(name + "\n")
    assert linux.find_stub_bus(tmp_path) == 3
    assert linux.find_stub_bus(tmp_path / "missing") is None


@pytest.mark.docker
@pytest.mark.parametrize("seed", range(8))
def test_oom_live(tmp_path, seed):
    label = inject("oom_alloc_failure", seed, tmp_path)
    assert label["trigger_status"] == "triggered", label
    out = (tmp_path / "artefacts" / "stdout.txt").read_text(encoding="utf-8")
    err = (tmp_path / "artefacts" / "stderr.txt").read_text(encoding="utf-8")
    if label["injected_param"]["mode"] == "rlimit_as":
        assert "MemoryError" in err
    else:
        assert "python_exit=137" in out and "oom_kill 1" in out


@pytest.mark.linux_i2c
def test_i2c_live(tmp_path):
    label = inject("i2c_sensor_nack", 0, tmp_path)
    assert label["trigger_status"] == "triggered", label
    assert "OSError" in (tmp_path / "artefacts" / "stderr.txt").read_text()
