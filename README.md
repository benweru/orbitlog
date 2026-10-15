# OrbitLog

An open, reproducible benchmark for **onboard spacecraft fault diagnosis with small language models under hard memory caps**.

## Headline target

> Gemma 4 E2B (text-only) names the correct root cause on **≥80% of 60 held-out spacecraft faults** while capped at **512 MiB of RAM**, about 92% below the 6.11 GiB bf16 text checkpoint, losing no more than 10 points against the unconstrained Q4_0 baseline.

The 80% is a placeholder. It gets fixed at (Baseline B − 10 points) in `PREREGISTRATION.md` before any compression runs.

What it produces:
- **Labelled fault dataset**: 15 fault classes injected into NASA cFS (in Docker) and a Linux payload app. Labels are written before each fault fires, so they're correct by construction.
- **E1: accuracy vs. memory curve** from 128 MiB to 4 GiB, measured with cgroup v2 `memory.peak`.
- **E2: compact downlink frame** aiming for ≥95% byte reduction (vs. ~64% for free-text summaries) without losing the diagnosis.

Caveat: these are emulated faults on a ground Linux machine, not flight data.

Full plan: [docs/plan.md](docs/plan.md).

## Status

Scaffolding only. Modules are stubs with TODOs and there are no results yet.

## Setup

Requires Python ≥3.11 (invoked as `python`), `make`, `git`, Docker.

```bash
git clone https://github.com/benweru/orbitlog.git
cd orbitlog
make setup     # creates .venv and installs orbitlog + dev deps
make test      # runs pytest
make quick     # 3 configs x 10 cases smoke benchmark (not yet implemented)
make reproduce # full pipeline (not yet implemented)
```

Override the interpreter with `make setup PYTHON=python3.11` if needed.

## Layout

```
src/orbitlog/faults/injector.py  fault injection (cFS + payload app)
src/orbitlog/dataset.py          case schema, splits, loading
src/orbitlog/eval.py             accuracy scoring, Wilson CIs
src/orbitlog/memory.py           cgroup v2 memory measurement
configs/fault_classes.yaml       the 15 fault classes
docker/cfs/Dockerfile            cFS image (placeholder)
docs/plan.md                     full project plan
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how work is split.
