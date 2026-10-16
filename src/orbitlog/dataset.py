"""Dataset: label schema, case loading and seed-based splits.

Target: >=50 train/dev + 60 held-out test cases (incl. 10 no-fault),
split by instance seed, with some unseen parameters in test.
"""
import json
from pathlib import Path

import jsonschema

TRIGGER_STATUSES = ("pending", "triggered", "failed")

LABEL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["fault_class", "component", "injected_param", "timestamp", "seed", "trigger_status"],
    "additionalProperties": False,
    "properties": {
        "fault_class": {"type": "string", "pattern": "^[a-z0-9_]+$"},
        "component": {"type": "string", "minLength": 1},
        "injected_param": {"type": "object"},
        "timestamp": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$"},
        "seed": {"type": "integer", "minimum": 0},
        "trigger_status": {"enum": list(TRIGGER_STATUSES)},
        "trigger_error": {"type": "string"},
    },
}


def validate_label(label: dict) -> None:
    """Raise jsonschema.ValidationError if the label is malformed."""
    jsonschema.validate(label, LABEL_SCHEMA)


def load_label(path: str | Path) -> dict:
    """Load and validate one label.json."""
    label = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_label(label)
    return label


def split_by_seed(seeds: list[int], test_fraction: float = 0.5) -> dict:
    """TODO(sprint 4): deterministic seed-based train/dev/test split."""
    raise NotImplementedError


def load_cases(path: str) -> list[dict]:
    """TODO(sprint 4): load a case directory (label + artefacts)."""
    raise NotImplementedError
