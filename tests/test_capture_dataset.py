import json
import os
import subprocess
from pathlib import Path

import jsonschema
import pytest

from orbitlog import build_dataset as bd
from orbitlog import capture
from orbitlog.capture import parse_evs, parse_evs_line
from orbitlog.faults import injector as inj_mod

HAS_DEV_FULL = os.path.exists("/dev/full")
BOOT = (Path(__file__).parent / "fixtures" / "cfs_boot_pr3.log").read_text()


def test_parse_real_boot_log():
    events = parse_evs(BOOT)
    assert [(e["app"], e["event_id"]) for e in events] == [
        ("CFE_ES", 1), ("CFE_ES", 2), ("CFE_ES", 91), ("CFE_EVS", 1), ("CFE_SB", 1)]
    first = events[0]
    assert first["scid"] == 66 and first["cpu"] == 1 and first["port"] == 1
    assert first["cfs_time"] == "1980-012-14:03:20.05160"
    assert first["text"].startswith("cFE ES Initialized: CFE_ES v7.0.1")


def test_parse_ignores_non_evs_and_strips_docker_timestamp():
    assert parse_evs_line("1980-012-14:03:20.60713 CFE_ES_Main: CFE_ES_Main entering OPERATIONAL state") is None
    line = next(l for l in BOOT.splitlines() if "CFE_SB 1:" in l)
    e = parse_evs_line("2026-10-16T09:00:00.123456789Z " + line)
    assert e["docker_ts"] == "2026-10-16T09:00:00.123456789Z" and e["app"] == "CFE_SB"


# Real line from Ben's Windows machine (PR #6 image, table_load_validation, seed 1):
# another app's progress "." arrived on the same line.
REAL_TBL96 = (".EVS Port1 1980-012-14:03:25.90003 66/1/CFE_TBL 96: SAMPLE_APP validation failed "
              "for SAMPLE_APP.ExampleTable 'inactive', Status=0xFFFFFFFF")
# Real line from the PR #6 body (cfs_app_crash_restart, seed 1).
REAL_ES10 = "EVS Port1 1980-012-14:03:26.75614 66/1/CFE_ES 10: Restart Application FAULT_APP Completed, AppID=1114134"


def test_parse_evs_mid_line_real_tbl96():
    e = parse_evs_line(REAL_TBL96)
    assert (e["app"], e["event_id"]) == ("CFE_TBL", 96)
    assert e["text"].startswith("SAMPLE_APP validation failed")
    e = parse_evs_line("2026-10-16T12:34:48.530164253Z " + REAL_TBL96)
    assert e["docker_ts"] == "2026-10-16T12:34:48.530164253Z" and e["event_id"] == 96


def test_parse_real_es10():
    e = parse_evs_line(REAL_ES10)
    assert (e["app"], e["event_id"]) == ("CFE_ES", 10)
    assert e["text"] == "Restart Application FAULT_APP Completed, AppID=1114134"


class _Box:
    def __init__(self, name):
        self.name = name


class _Inj:
    def __init__(self, container=None):
        self.container = container


def _fake_docker(monkeypatch, text, rc=0, calls=None):
    def fake_run(cmd, **kw):
        if calls is not None:
            calls.append(cmd)
        return subprocess.CompletedProcess(cmd, rc, stdout=text if rc == 0 else "", stderr="" if rc == 0 else "boom")
    monkeypatch.setattr(capture.shutil, "which", lambda x: "/usr/bin/docker")
    monkeypatch.setattr(capture.subprocess, "run", fake_run)


def test_capture_unavailable_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "container_running", lambda name: False)
    meta = capture.capture(_Inj(), tmp_path / "a", capture.now_utc())
    assert meta["capture"] == "unavailable" and meta["capture_source"] is None
    assert not (tmp_path / "a").exists()


def test_capture_prefers_case_container_and_never_overwrites(tmp_path, monkeypatch):
    calls = []
    _fake_docker(monkeypatch, BOOT + REAL_TBL96 + "\n", calls=calls)
    monkeypatch.setattr(capture, "container_running", lambda name: True)
    adir = tmp_path / "a"
    adir.mkdir()
    (adir / "container.log").write_text("injector's own log")
    meta = capture.capture(_Inj(_Box("orbitlog-cfs-table_load_validation-1")), adir, capture.now_utc())
    assert calls == [["docker", "logs", "--timestamps", "orbitlog-cfs-table_load_validation-1"]]
    assert meta["capture"] == "captured" and meta["capture_source"] == "case_container"
    assert (adir / "container.log").read_text() == "injector's own log"
    assert (adir / capture.CAPTURE_LOG).read_text() == BOOT + REAL_TBL96 + "\n"
    evs = [json.loads(l) for l in (adir / "evs.jsonl").read_text().splitlines()]
    assert len(evs) == 6 and (evs[-1]["app"], evs[-1]["event_id"]) == ("CFE_TBL", 96)


def test_capture_shared_container_uses_window(tmp_path, monkeypatch):
    calls = []
    _fake_docker(monkeypatch, BOOT, calls=calls)
    monkeypatch.setattr(capture, "container_running", lambda name: True)
    start = capture.now_utc()
    meta = capture.capture(_Inj(), tmp_path / "a", start)
    cmd = calls[0]
    assert cmd[-1] == "orbitlog-cfs" and cmd[cmd.index("--since") + 1] == start
    assert cmd[cmd.index("--until") + 1] == meta["capture_end"]
    assert meta["capture_source"] == "shared_container"


def test_capture_error_is_recorded(tmp_path, monkeypatch):
    _fake_docker(monkeypatch, "", rc=1)
    meta = capture.capture(_Inj(_Box("x")), tmp_path / "a", capture.now_utc())
    assert meta["capture"] == "error" and meta["capture_error"] == "boom"
    assert not (tmp_path / "a").exists()


def test_plan_is_deterministic_and_cycles():
    classes = ["disk_full", "corrupt_input_file", "payload_python_exception"]
    a, b = bd.plan(9, 0, classes), bd.plan(9, 0, list(reversed(classes)))
    assert a == b
    assert [e["fault_class"] for e in a[:3]] == sorted(classes)
    assert bd.plan(9, 1, classes) != a
    with pytest.raises(ValueError):
        bd.plan(3, 0, [])


def _strip(rows):
    # Timestamps (label, payload.log) and temp paths (tracebacks) differ between runs;
    # everything the plan and labels determine must not.
    keep = ("case_id", "fault_class", "component", "seed", "trigger_status", "capture")
    return [{**{k: r[k] for k in keep}, "paths": [a["path"] for a in r["artefacts"]]} for r in rows]


@pytest.fixture
def no_docker(monkeypatch):
    monkeypatch.setattr(capture, "container_running", lambda name: False)


def test_build_end_to_end_and_reproducible(tmp_path, no_docker):
    rows1 = bd.build(6, 0, tmp_path / "d1")
    rows2 = bd.build(6, 0, tmp_path / "d2")
    assert _strip(rows1) == _strip(rows2)
    for a, b in zip(rows1, rows2):
        la = json.loads((tmp_path / "d1" / "cases" / a["case_id"] / "label.json").read_text())
        lb = json.loads((tmp_path / "d2" / "cases" / b["case_id"] / "label.json").read_text())
        la.pop("timestamp"), lb.pop("timestamp")
        assert la == lb
    manifest = [json.loads(l) for l in (tmp_path / "d1" / "manifest.jsonl").read_text().splitlines()]
    assert len(manifest) == 6
    for row in manifest:
        jsonschema.validate(row, bd.MANIFEST_SCHEMA)
        expected = "triggered" if (row["fault_class"] != "disk_full" or HAS_DEV_FULL) else "failed"
        assert row["trigger_status"] == expected and row["capture"] == "unavailable"
        case = tmp_path / "d1" / "cases" / row["case_id"]
        assert json.loads((case / "label.json").read_text())["seed"] == row["seed"]
        for a in row["artefacts"]:
            assert bd._sha256(case / a["path"]) == a["sha256"]
        assert not (case / "work").exists()
    assert {r["fault_class"] for r in manifest} == {"disk_full", "corrupt_input_file", "payload_python_exception"}


class _NeverTriggers(inj_mod.FaultInjector):
    component = "probe"

    def choose_params(self, rng):
        return {}

    def trigger(self):
        raise RuntimeError("could not inject")

    def collect(self, out_dir):
        return []


def test_failed_cases_are_kept(tmp_path, no_docker, monkeypatch):
    monkeypatch.setitem(inj_mod._REGISTRY, "watchdog_reset", _NeverTriggers)
    rows = bd.build(4, 0, tmp_path, classes=["watchdog_reset", "corrupt_input_file"])
    st = {r["fault_class"]: r["trigger_status"] for r in rows}
    assert st == {"watchdog_reset": "failed", "corrupt_input_file": "triggered"}
    assert len((tmp_path / "manifest.jsonl").read_text().splitlines()) == 4


def test_manifest_schema_rejects_bad_rows():
    good = {"case_id": "c0000-disk_full", "fault_class": "disk_full", "component": "x", "seed": 1,
            "trigger_status": "triggered", "artefacts": [], "capture": "unavailable",
            "orbitlog_commit": "abc"}
    jsonschema.validate(good, bd.MANIFEST_SCHEMA)
    for bad in ({**good, "capture": "maybe"}, {**good, "trigger_status": "pending"},
                {**good, "artefacts": [{"path": "x", "sha256": "nothex", "bytes": 1}]}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, bd.MANIFEST_SCHEMA)


def test_capture_runs_before_cleanup_even_on_failed_trigger(tmp_path, no_docker, monkeypatch):
    order = []

    class _OwnContainer(_NeverTriggers):
        def __init__(self, workdir):
            super().__init__(workdir)
            self.container = _Box("orbitlog-cfs-probe")

        def cleanup(self):
            order.append("cleanup")
            self.container = None

    def fake_capture(injector, adir, start, shared_name="orbitlog-cfs"):
        order.append(("capture", capture.case_container_name(injector)))
        return {"capture": "unavailable", "capture_start": start, "capture_end": start,
                "capture_source": None, "container": None}

    monkeypatch.setitem(inj_mod._REGISTRY, "watchdog_reset", _OwnContainer)
    monkeypatch.setattr(bd.cap_mod, "capture", fake_capture)
    rows = bd.build(1, 0, tmp_path, classes=["watchdog_reset"])
    assert order == [("capture", "orbitlog-cfs-probe"), "cleanup"]
    assert rows[0]["trigger_status"] == "failed"
