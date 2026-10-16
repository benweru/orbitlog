import pytest

from orbitlog.faults.injector import inject

pytestmark = pytest.mark.cfs


def _log(tmp_path):
    return (tmp_path / "artefacts" / "container.log").read_text(encoding="utf-8")


def test_table_load_validation(tmp_path):
    label = inject("table_load_validation", 1, tmp_path)
    assert label["trigger_status"] == "triggered", label
    assert label["injected_param"]["Int1"] > 10
    assert "validation failed for" in _log(tmp_path)


def test_sb_pipe_full(tmp_path):
    """The pipe does not overflow. The label must stay failed, not a fake event."""
    label = inject("sb_pipe_full", 1, tmp_path)
    assert label["trigger_status"] == "failed", label
    assert label["injected_param"]["noop_count"] > label["injected_param"]["pipe_depth"]
    assert "0 overflow lines" in label["trigger_error"]
    assert "NOOP lines" in label["trigger_error"]


def test_cfs_app_crash_restart(tmp_path):
    label = inject("cfs_app_crash_restart", 1, tmp_path)
    assert label["trigger_status"] == "triggered", label
    log = _log(tmp_path)
    assert "Restart Application FAULT_APP" in log
    assert "Exit Application FAULT_APP" in log
