"""Fault injector interface and registry.

inject() writes and fsyncs the ground-truth label BEFORE the fault is
triggered, so labels are correct by construction. If triggering fails the
label is kept and marked trigger_status: failed; labels are never rewritten
after the fact except to record that status.
"""
from __future__ import annotations

import json
import os
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from orbitlog.dataset import validate_label
from orbitlog.faults import load_fault_classes

LABEL_FILE = "label.json"
_REGISTRY: dict[str, type["FaultInjector"]] = {}


def register(name: str):
    """Class decorator: register an injector under a fault class name from the YAML."""
    known = {c["name"] for c in load_fault_classes()}
    if name not in known:
        raise ValueError(f"unknown fault class {name!r}; add it to configs/fault_classes.yaml")

    def deco(cls):
        if name in _REGISTRY:
            raise ValueError(f"fault class {name!r} already registered")
        cls.fault_class = name
        _REGISTRY[name] = cls
        return cls
    return deco


def get_injector(name: str) -> type["FaultInjector"]:
    known = {c["name"] for c in load_fault_classes()}
    if name not in known:
        raise KeyError(f"unknown fault class {name!r}")
    if name not in _REGISTRY:
        raise NotImplementedError(f"injector for {name!r} not yet implemented")
    return _REGISTRY[name]


def registered() -> list[str]:
    return sorted(_REGISTRY)


class FaultInjector(ABC):
    """One fault instance. Subclasses must derive all parameters from the seed."""

    fault_class: str = ""
    component: str = ""

    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        self.params: dict = {}
        self.seed: int | None = None

    def prepare(self, seed: int) -> dict:
        """Set up state and return injected_param. Must be deterministic in seed."""
        self.seed = seed
        self.params = self.choose_params(random.Random(seed))
        self.setup()
        return self.params

    @abstractmethod
    def choose_params(self, rng: random.Random) -> dict:
        """Return injected parameters using only rng."""

    def setup(self) -> None:
        """Optional: create inputs in self.workdir."""

    @abstractmethod
    def trigger(self) -> None:
        """Fire the fault. Raise only if the fault could NOT be triggered."""

    @abstractmethod
    def collect(self, out_dir: Path) -> list[str]:
        """Copy real artefacts into out_dir; return their file names."""

    def cleanup(self) -> None:
        """Optional: restore state."""


def _write_label(path: Path, label: dict) -> None:
    validate_label(label)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(label, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def inject(fault_class: str, seed: int, out_dir: str | Path) -> dict:
    """Run one fault instance: label (fsync) -> trigger -> collect -> cleanup."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    inj = get_injector(fault_class)(work)
    params = inj.prepare(seed)
    label = {
        "fault_class": fault_class,
        "component": inj.component,
        "injected_param": params,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "trigger_status": "pending",
    }
    label_path = out / LABEL_FILE
    _write_label(label_path, label)
    try:
        try:
            inj.trigger()
        except Exception as e:  # the fault could not be injected
            label["trigger_status"] = "failed"
            label["trigger_error"] = f"{type(e).__name__}: {e}"
            _write_label(label_path, label)
            return label
        label["trigger_status"] = "triggered"
        _write_label(label_path, label)
        inj.collect(out / "artefacts")
        return label
    finally:
        inj.cleanup()


# Register the implemented classes.
from orbitlog.faults import classes as _classes  # noqa: E402,F401
