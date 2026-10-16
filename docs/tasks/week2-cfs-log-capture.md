# Week 2: cFS log capture and dataset builder

- **Owner:** Grok Bot (works on the box)
- **Branch:** `feat/cfs-log-capture`
- **PR title:** `feat(dataset): capture cFS logs and build seeded case manifest`

## Goal
Every fault case ends up as a self-contained folder: the label, the payload artefacts, and the cFS event messages and container logs from the fault window. `make dataset N=<n> SEED=<s>` builds N seeded cases and writes a manifest.

## Context
- docs/plan.md §4 (dataset and split by seed) and §6 (reproducible from seeds).
- The existing `inject()` (PR #2) writes `label.json` first, then `artefacts/`.
- `make cfs-up` runs the container `orbitlog-cfs`. cFS prints EVS events to stdout, and `docker logs` shows the same stream.
- The cFS injectors come from Ben's `feat/cfs-fault-injectors`. This task must work without them: it builds with the 3 host classes and picks up the cFS classes once they're registered.

## Steps
1. **`src/orbitlog/capture.py`:**
   - `ContainerLogCapture(name)` is a context manager. It records the UTC start and end times and saves `docker logs --since <start> --until <end> --timestamps` to `artefacts/container.log`.
   - If Docker or the container isn't available, it writes nothing and records `capture: unavailable` in the case metadata. It never writes a fake log.
2. **EVS parser:** pull out the events from container.log that look like EVS messages (app name, event ID, type, text) and save them as `artefacts/evs.jsonl`. Unit-test it on real lines copied from Ben's boot log in PR #3, not invented ones.
3. **`src/orbitlog/build_dataset.py`:**
   - Inputs: N, a base seed and a list of classes (default: every registered class).
   - Plan the cases deterministically, cycling through the classes, with per-case seeds taken from the base seed.
   - Run `inject()` for each case into `data/cases/<case_id>/`.
   - Write `data/manifest.jsonl`. Each line holds `case_id`, `fault_class`, `component`, `seed`, `trigger_status`, the artefact list with sha256 for each file, the capture status and the orbitlog git commit.
   - Validate every label with `LABEL_SCHEMA`. Cases whose trigger failed are **kept** in the manifest, flagged as failed.
4. **Makefile:** `dataset` target, `$(PYTHON) -m orbitlog.build_dataset --n $(N) --seed $(SEED)`, with defaults N=30 and SEED=0. `data/cases/` is gitignored. Only a small sample fixture is committed for tests.
5. **Tests:**
   - Running twice with the same seed gives the same plan and labels (timestamps excluded).
   - The manifest matches its schema.
   - Failed cases are kept.
   - The capture degrades cleanly without Docker.
   - End to end, N=6 builds with the host classes in `tmp_path`.

## Acceptance criteria
- [ ] `make dataset N=30` on the box builds 30 cases with the 3 host classes. The real manifest summary (count per class and per status) is pasted into the PR.
- [ ] With the cFS container running, cases contain `container.log` and `evs.jsonl`. If cFS injectors haven't merged yet, show that with a container running during a host-class case.
- [ ] `make test` passes without Docker.
- [ ] No hand-edited or synthetic log content.

## Out of scope
- The cFS fault classes themselves (Ben's `feat/cfs-fault-injectors`).
- The train/dev/test split, distractor noise and the held-out "no fault" cases. Those are week 3–4.
- Model inference.
