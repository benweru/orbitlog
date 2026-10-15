"""Fault injector.

Writes the ground-truth label {class, component, injected_param, timestamp}
BEFORE triggering a fault, so labels are correct by construction.
Targets: NASA cFS in Docker (docker/cfs) and a Python payload app.
"""
from dataclasses import dataclass


@dataclass
class InjectionLabel:
    fault_class: str
    component: str
    injected_param: dict
    timestamp: str
    seed: int


def inject(fault_class: str, seed: int, out_dir: str) -> InjectionLabel:
    """Inject one fault instance and capture artefacts (EVS, HK, syslog/dmesg, traces).

    TODO(week 2): first 5 classes; TODO(weeks 3-4): all 15 + distractor noise.
    """
    raise NotImplementedError("fault injection not yet implemented")
