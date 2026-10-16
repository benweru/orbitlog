import pytest

from orbitlog.capture import parse_evs
from orbitlog.faults.cfs import keep_container_log
from orbitlog.faults.injector import inject

pytestmark = pytest.mark.cfs


def _events(tmp_path):
    """(app, event_id) -> text of the LAST such event; boot events come first."""
    log = (tmp_path / "artefacts" / "container.log").read_text(encoding="utf-8")
    return {(e["app"], e["event_id"]): e["text"] for e in parse_evs(log)}


def test_table_load_validation(tmp_path):
    label = inject("table_load_validation", 1, tmp_path)
    assert label["trigger_status"] == "triggered", label
    assert label["injected_param"]["Int1"] > 10
    ev = _events(tmp_path)
    assert ("CFE_TBL", 12) in ev
    assert "validation failed for SAMPLE_APP.ExampleTable" in ev[("CFE_TBL", 96)]


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_sb_pipe_full_overflows(tmp_path, seed):
    label = inject("sb_pipe_full", seed, tmp_path)
    assert label["trigger_status"] == "triggered", label
    assert label["injected_param"]["burst_count"] > 2 * label["injected_param"]["pipe_depth"]
    text = _events(tmp_path)[("CFE_SB", 25)]
    assert text.startswith("Pipe Overflow") and "SLOW_APP_CMD" in text


def test_cfs_app_crash_restart(tmp_path):
    label = inject("cfs_app_crash_restart", 1, tmp_path)
    assert label["trigger_status"] == "triggered", label
    ev = _events(tmp_path)
    assert "FAULT_APP" in ev[("CFE_ES", 10)]
    assert "FAULT_APP" in ev[("CFE_ES", 14)]


def test_failed_trigger_keeps_container_log(tmp_path, monkeypatch):
    from orbitlog.faults import cfs

    def never(self):
        self._boot()
        raise RuntimeError("forced failure after boot")

    monkeypatch.setattr(cfs.TableLoadValidation, "trigger", never)
    label = inject("table_load_validation", 1, tmp_path, before_cleanup=keep_container_log)
    assert label["trigger_status"] == "failed"
    log = (tmp_path / "artefacts" / "container.log").read_text(encoding="utf-8")
    assert "CFE_ES_Main entering OPERATIONAL" in log
