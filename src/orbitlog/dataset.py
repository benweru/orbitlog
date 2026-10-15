"""Dataset: case schema, seed-based splits and loading.

Target: >=50 train/dev + 60 held-out test cases (incl. 10 no-fault),
split by instance seed, with some unseen parameters in test.
"""

CASE_FIELDS = ("case_id", "fault_class", "component", "log_bundle", "split", "seed")


def split_by_seed(seeds: list[int], test_fraction: float = 0.5) -> dict:
    """TODO(week 3): deterministic seed-based train/dev/test split."""
    raise NotImplementedError


def load_cases(path: str) -> list[dict]:
    """TODO(week 2): load and validate cases (JSON schema)."""
    raise NotImplementedError
