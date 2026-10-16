import json
import subprocess
from pathlib import Path

import jsonschema
import pytest

from orbitlog import build_dataset as bd
from orbitlog import capture
from orbitlog.capture import ContainerLogCapture, parse_evs, parse_evs_line
from orbitlog.faults import injector as inj_mod

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


def test_capture_unavailable_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "container_running", lambda name: False)
    with ContainerLogCapture(tmp_path / "a") as cap:
        pass
    assert cap.status == "unavailable" and cap.files == []
    assert not (tmp_path / "a").exists()
    assert cap.meta()["capture_start"] <= cap.meta()["capture_end"]


def test_capture_saves_docker_logs_window(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=BOOT, stderr="")

    monkeypatch.setattr(capture, "container_running", lambda name: True)
    monkeypatch.setattr(capture.subprocess, "run", fake_run)
    with ContainerLogCapture(tmp_path / "a", name="orbitlog-cfs") as cap:
        pass
    cmd = calls[0]
    assert cmd[:3] == ["docker", "logs", "--timestamps"]
    assert cmd[cmd.index("--since") + 1] == cap.start and cmd[cmd.index("--until") + 1] == cap.end
    assert (tmp_path / "a" / "container.log").read_text() == BOOT
    evs = [json.loads(l) for l in (tmp_path / "a" / "evs.jsonl").read_text().splitlines()]
    assert len(evs) == 5 and cap.status == "captured"


def test_capture_error_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "container_running", lambda name: True)
    monkeypatch.setattr(capture.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    with ContainerLogCapture(tmp_path / "a") as cap:
        pass
    assert cap.status == "error" and cap.meta()["capture_error"] == "boom"
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
        assert row["trigger_status"] == "triggered" and row["capture"] == "unavailable"
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
