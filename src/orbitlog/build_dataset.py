"""Build N seeded fault cases and a manifest.

    python -m orbitlog.build_dataset --n 30 --seed 0 [--out data] [--classes a,b]

Cases go to <out>/cases/<case_id>/ and the manifest to <out>/manifest.jsonl.
Cases whose trigger failed are kept and flagged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema

from orbitlog import capture as cap_mod
from orbitlog.dataset import load_label
from orbitlog.faults.injector import inject, registered

MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["case_id", "fault_class", "component", "seed", "trigger_status",
                 "artefacts", "capture", "orbitlog_commit"],
    "properties": {
        "case_id": {"type": "string", "pattern": "^c[0-9]{4}-[a-z0-9_]+$"},
        "fault_class": {"type": "string"},
        "component": {"type": "string"},
        "seed": {"type": "integer", "minimum": 0},
        "trigger_status": {"enum": ["triggered", "failed"]},
        "artefacts": {"type": "array", "items": {
            "type": "object", "required": ["path", "sha256", "bytes"],
            "properties": {"path": {"type": "string"},
                           "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                           "bytes": {"type": "integer"}}}},
        "capture": {"enum": ["captured", "unavailable", "error"]},
        "orbitlog_commit": {"type": "string"},
        "orbitlog_dirty": {"type": "boolean"},
        "capture_source": {"enum": ["case_container", "shared_container", None]},
    },
}


def plan(n: int, base_seed: int, classes: list[str]) -> list[dict]:
    """Deterministic case plan: cycle through classes, per-case seeds from base seed."""
    if not classes:
        raise ValueError("no fault classes to build")
    rng = random.Random(base_seed)
    classes = sorted(classes)
    return [{"case_id": f"c{i:04d}-{classes[i % len(classes)]}",
             "fault_class": classes[i % len(classes)],
             "seed": rng.randrange(0, 2**31)} for i in range(n)]


def _git() -> tuple[str, bool]:
    try:
        root = Path(__file__).resolve().parents[2]
        h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root,
                                    capture_output=True, text=True).stdout.strip())
        return h, dirty
    except Exception:
        return "unknown", False


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build_case(entry: dict, cases_dir: Path, commit: str, dirty: bool, container: str) -> dict:
    case_dir = cases_dir / entry["case_id"]
    if case_dir.exists():
        shutil.rmtree(case_dir)
    start = cap_mod.now_utc()
    meta: dict = {}

    def hook(injector, out):
        meta.update(cap_mod.capture(injector, out / "artefacts", start, shared_name=container))

    inject(entry["fault_class"], entry["seed"], case_dir, before_cleanup=hook)
    if not meta:  # hook raised; record honestly
        meta = {"capture": "error", "capture_error": "capture hook raised"}
    shutil.rmtree(case_dir / "work", ignore_errors=True)  # inputs are regenerable from the seed
    label = load_label(case_dir / "label.json")
    files = sorted(p for p in case_dir.rglob("*") if p.is_file())
    row = {
        "case_id": entry["case_id"],
        "fault_class": label["fault_class"],
        "component": label["component"],
        "seed": label["seed"],
        "trigger_status": label["trigger_status"],
        "artefacts": [{"path": str(p.relative_to(case_dir)), "sha256": _sha256(p),
                       "bytes": p.stat().st_size} for p in files],
        "orbitlog_commit": commit,
        "orbitlog_dirty": dirty,
        **meta,
    }
    jsonschema.validate(row, MANIFEST_SCHEMA)
    return row


def build(n: int, seed: int, out: str | Path, classes: list[str] | None = None,
          container: str = "orbitlog-cfs") -> list[dict]:
    out = Path(out)
    cases_dir = out / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    commit, dirty = _git()
    rows = [build_case(e, cases_dir, commit, dirty, container)
            for e in plan(n, seed, classes or registered())]
    with open(out / "manifest.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return rows


def summarize(rows: list[dict]) -> str:
    lines = [f"cases: {len(rows)}"]
    for k in ("fault_class", "trigger_status", "capture"):
        c = Counter(r[k] for r in rows)
        lines.append(f"by {k}: " + ", ".join(f"{a}={b}" for a, b in sorted(c.items())))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data")
    ap.add_argument("--classes", default="", help="comma-separated; default all registered")
    ap.add_argument("--container", default="orbitlog-cfs")
    a = ap.parse_args(argv)
    classes = [c for c in a.classes.split(",") if c] or None
    rows = build(a.n, a.seed, a.out, classes, a.container)
    print(summarize(rows))
    print(f"manifest: {Path(a.out) / 'manifest.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
