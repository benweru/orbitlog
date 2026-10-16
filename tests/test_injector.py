import json
import random
import sys

import jsonschema
import pytest

from orbitlog.dataset import load_label, validate_label
from orbitlog.faults import load_fault_classes
from orbitlog.faults import injector as inj_mod
from orbitlog.faults.injector import FaultInjector, get_injector, inject, register, registered

IMPLEMENTED = [
    "cfs_app_crash_restart",
    "corrupt_input_file",
    "disk_full",
    "payload_python_exception",
    "sb_pipe_full",
    "table_load_validation",
]
PAYLOAD = ["corrupt_input_file", "disk_full", "payload_python_exception"]
linux_only = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="/dev/full is Linux-only")


def test_registry_has_the_implemented_classes():
    assert registered() == IMPLEMENTED


def test_other_classes_raise_not_implemented():
    others = [c["name"] for c in load_fault_classes() if c["name"] not in IMPLEMENTED]
    assert len(others) == 9
    for name in others:
        with pytest.raises(NotImplementedError):
            get_injector(name)


def test_unknown_class_rejected():
    with pytest.raises(KeyError):
        get_injector("not_a_class")
    with pytest.raises(ValueError):
        register("not_a_class")


def test_label_schema_rejects_bad_labels():
    good = {"fault_class": "disk_full", "component": "x", "injected_param": {},
            "timestamp": "2026-10-15T12:00:00+00:00", "seed": 1, "trigger_status": "pending"}
    validate_label(good)
    for bad in ({**good, "trigger_status": "done"}, {**good, "seed": -1},
                {k: v for k, v in good.items() if k != "component"}, {**good, "extra": 1},
                {**good, "timestamp": "yesterday"}):
        with pytest.raises(jsonschema.ValidationError):
            validate_label(bad)


class _Probe(FaultInjector):
    component = "probe"
    seen_label = None
    fail = False

    def choose_params(self, rng):
        return {"x": rng.randint(0, 1000)}

    def trigger(self):
        p = self.workdir.parent / "label.json"
        assert p.exists(), "label must be written before trigger"
        type(self).seen_label = json.loads(p.read_text())
        if self.fail:
            raise RuntimeError("could not inject")

    def collect(self, out_dir):
        return []


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.setitem(inj_mod._REGISTRY, "watchdog_reset", _Probe)
    _Probe.seen_label, _Probe.fail = None, False
    return _Probe


def test_label_written_before_trigger(probe, tmp_path):
    label = inject("watchdog_reset", 7, tmp_path)
    assert probe.seen_label["trigger_status"] == "pending"
    assert probe.seen_label["injected_param"] == label["injected_param"]
    assert load_label(tmp_path / "label.json")["trigger_status"] == "triggered"


def test_label_fsynced_before_trigger(probe, tmp_path, monkeypatch):
    events = []
    real = inj_mod.os.fsync
    monkeypatch.setattr(inj_mod.os, "fsync", lambda fd: (events.append("fsync"), real(fd)))
    orig = _Probe.trigger
    monkeypatch.setattr(_Probe, "trigger", lambda self: (events.append("trigger"), orig(self)))
    inject("watchdog_reset", 1, tmp_path)
    assert "fsync" in events and events.index("fsync") < events.index("trigger")


def test_failed_trigger_keeps_label(probe, tmp_path):
    probe.fail = True
    label = inject("watchdog_reset", 3, tmp_path)
    saved = load_label(tmp_path / "label.json")
    assert saved["trigger_status"] == "failed" == label["trigger_status"]
    assert "could not inject" in saved["trigger_error"]
    assert saved["fault_class"] == "watchdog_reset"


@pytest.mark.parametrize("name", IMPLEMENTED)
def test_seed_determinism(name, tmp_path):
    cls = get_injector(name)
    a = cls(tmp_path / "a"); (tmp_path / "a").mkdir()
    b = cls(tmp_path / "b"); (tmp_path / "b").mkdir()
    if name == "disk_full" and not sys.platform.startswith("linux"):
        pytest.skip("Linux only")
    assert a.prepare(42) == b.prepare(42)
    if name in PAYLOAD:
        assert (tmp_path / "a" / "frame.olim").read_bytes() == (tmp_path / "b" / "frame.olim").read_bytes()
    params = [cls(tmp_path / f"s{s}").choose_params(random.Random(s)) for s in range(20)]
    unique = {json.dumps(p, sort_keys=True) for p in params}
    if name == "cfs_app_crash_restart":
        assert len(unique) == 1
    else:
        assert len(unique) > 1


def _run(name, seed, tmp_path):
    label = inject(name, seed, tmp_path)
    assert label["trigger_status"] == "triggered", label
    art = tmp_path / "artefacts"
    stderr = (art / "stderr.txt").read_text()
    log = (art / "payload.log").read_text()
    assert int((art / "exit_code.txt").read_text()) != 0
    assert "Traceback" in stderr and "payload failed" in log
    return label, stderr


@linux_only
@pytest.mark.parametrize("seed", range(3))
def test_disk_full_end_to_end(seed, tmp_path):
    _, stderr = _run("disk_full", seed, tmp_path)
    assert "No space left on device" in stderr


@pytest.mark.parametrize("seed", range(6))
def test_payload_exception_end_to_end(seed, tmp_path):
    label, stderr = _run("payload_python_exception", seed, tmp_path)
    expected = {"invert": "IndexError", "stats": "ZeroDivisionError", "metadata": "KeyError"}
    assert expected[label["injected_param"]["stage"]] in stderr


@pytest.mark.parametrize("seed", range(6))
def test_corrupt_input_end_to_end(seed, tmp_path):
    label, stderr = _run("corrupt_input_file", seed, tmp_path)
    assert "FrameError" in stderr
    expected = {"truncate": ("truncated", "too short"), "bitflip": ("crc mismatch", "truncated"),
                "bad_magic": ("bad magic",)}
    assert any(s in stderr for s in expected[label["injected_param"]["mode"]])
