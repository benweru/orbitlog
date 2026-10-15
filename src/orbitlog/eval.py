"""Evaluation.

Model output JSON: {root_cause_class, component, evidence_line, action}.
Correct = exact match on root_cause_class AND component.
"""
import math


def is_correct(pred: dict, label: dict) -> bool:
    """Primary metric: class and component both match."""
    return (
        pred.get("root_cause_class") == label.get("fault_class")
        and pred.get("component") == label.get("component")
    )


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def judge_action(pred: dict, label: dict) -> float:
    """TODO: LLM-judge action-appropriateness score (20% hand-checked)."""
    raise NotImplementedError
