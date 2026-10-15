from orbitlog import __version__
from orbitlog.eval import is_correct, wilson_interval
from orbitlog.faults import load_fault_classes
from orbitlog.memory import fingerprint


def test_version():
    assert __version__


def test_fifteen_fault_classes():
    classes = load_fault_classes()
    assert len(classes) == 15
    assert len({c["name"] for c in classes}) == 15


def test_is_correct():
    label = {"fault_class": "disk_full", "component": "payload"}
    assert is_correct({"root_cause_class": "disk_full", "component": "payload"}, label)
    assert not is_correct({"root_cause_class": "disk_full", "component": "cfs"}, label)


def test_wilson_interval_bounds():
    lo, hi = wilson_interval(48, 60)
    assert 0 <= lo < 0.8 < hi <= 1


def test_fingerprint():
    assert "release" in fingerprint()
