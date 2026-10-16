"""cFS event matching and failed-log retention, without Docker."""
import pytest

from orbitlog.cfs import container as container_mod
from orbitlog.cfs.container import CfsContainer
from orbitlog.faults import cfs
from orbitlog.faults.injector import inject

# Real lines from table_load_validation runs on Ben's Windows machine.
TBL12 = ("EVS Port1 1980-012-14:03:21.55888 66/1/CFE_TBL 12: LoadFile,app=CFE_TBL,file=/cf/b42.tbl,"
         "tbl=SAMPLE_APP.ExampleTable:Successful load into working buffer")
TBL96 = (".EVS Port1 1980-012-14:03:25.90007 66/1/CFE_TBL 96: SAMPLE_APP validation failed for "
         "SAMPLE_APP.ExampleTable 'inactive', Status=0xFFFFFFFF")


class _FakeBox(CfsContainer):
    def __init__(self, text):
        super().__init__("fake")
        self.text = text

    def logs(self):
        return self.text


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(container_mod.time, "sleep", lambda s: None)


def test_wait_for_event_matches_app_and_id():
    e = _FakeBox(TBL12 + "\n" + TBL96 + "\n").wait_for_event("CFE_TBL", 96, timeout_s=1)
    assert e["text"].startswith("SAMPLE_APP validation failed")


def test_wait_for_event_ignores_loose_text_and_other_apps():
    # The phrase alone, or the right ID from another app, must not match.
    text = ("SAMPLE_APP validation failed for SAMPLE_APP.ExampleTable\n"
            "EVS Port1 1980-012-14:03:25.90002 66/1/SAMPLE_APP 96: validation failed for x\n")
    with pytest.raises(RuntimeError, match="CFE_TBL event 96"):
        _FakeBox(text).wait_for_event("CFE_TBL", 96, timeout_s=0.01)


def test_wait_for_event_subject_skips_same_id_for_other_app():
    # Real boot line from this machine: CFE_ES 14 for SBN precedes FAULT_APP's.
    sbn = "EVS Port1 1980-012-14:03:21.57891 66/1/CFE_ES 14: Exit Application SBN Completed."
    box = _FakeBox(sbn + "\n")
    with pytest.raises(RuntimeError, match="about 'FAULT_APP'"):
        box.wait_for_event("CFE_ES", 14, timeout_s=0.01, subject="FAULT_APP")
    assert box.wait_for_event("CFE_ES", 14, timeout_s=0.01)["text"].endswith("SBN Completed.")


def test_sb_pipe_full_params_always_exceed_twice_depth():
    for seed in range(200):
        p = cfs.SbPipeFull.__new__(cfs.SbPipeFull).choose_params(__import__("random").Random(seed))
        assert 2 * p["pipe_depth"] < p["burst_count"] <= 40
        assert p["msg_id"] == "0x18B9"


class _Boots(cfs.TableLoadValidation):
    def _boot(self):
        self.container = _FakeBox("booted\n" + TBL12 + "\n")
        self.container.stop = lambda: None
        return self.container

    def trigger(self):
        self._boot()
        raise RuntimeError("forced")


def test_keep_container_log_on_failed_trigger(tmp_path, monkeypatch):
    from orbitlog.faults import injector as inj_mod
    monkeypatch.setitem(inj_mod._REGISTRY, "table_load_validation", _Boots)
    label = inject("table_load_validation", 0, tmp_path, before_cleanup=cfs.keep_container_log)
    assert label["trigger_status"] == "failed"
    assert (tmp_path / "artefacts" / "container.log").read_text(encoding="utf-8") == "booted\n" + TBL12 + "\n"


def test_keep_container_log_ignores_non_cfs(tmp_path):
    cfs.keep_container_log(object(), tmp_path)
    assert not (tmp_path / "artefacts").exists()
