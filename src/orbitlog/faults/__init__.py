"""Fault classes and injection."""
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[3] / "configs" / "fault_classes.yaml"


def load_fault_classes(path: Path = CONFIG) -> list[dict]:
    """Return the fault class list from configs/fault_classes.yaml."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["classes"]
