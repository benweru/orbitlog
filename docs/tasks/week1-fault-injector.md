# Week 1: Fault injector core

- **Owner:** Grok Bot (works on the box)
- **Branch:** `feat/fault-injector-core`
- **PR title:** `feat(faults): add injector interface and first 3 fault classes`

## Goal
Define the injector interface and implement the first 3 fault classes. The ground-truth label is written **before** each fault is triggered, so labels are correct by construction (see docs/plan.md, section 4).

## Scope
1. Interface in `src/orbitlog/faults/injector.py`:
   - `FaultInjector` base class with `prepare(seed)`, `trigger()`, `collect(out_dir)` and `cleanup()`.
   - A registry that maps class names in `configs/fault_classes.yaml` to injector classes.
   - `inject(fault_class, seed, out_dir)` runs: build the label, then write `label.json` and fsync it, then trigger, then collect, then clean up. If triggering fails, the label is kept and marked `trigger_status: failed`, so failures can never be relabelled after the fact.
2. Label schema in `src/orbitlog/dataset.py`: `{fault_class, component, injected_param, timestamp (UTC ISO 8601), seed, trigger_status}`, validated with jsonschema.
3. The first 3 classes. These need no cFS, so they don't depend on Ben's task:
   - `disk_full`: fill a small size-limited tmpfs or loop file that the payload writes to.
   - `payload_python_exception`: a payload app that raises a seeded exception.
   - `corrupt_input_file`: hand the payload an input file truncated or bit-flipped from a seed.
   Parameters come from the seed, so the same seed gives the same injection.
4. Tests: the label is written before the trigger (checked with a mock trigger that asserts `label.json` exists), schema validation, seed determinism, and the 3 classes running end-to-end in a temp directory.

## Acceptance criteria
- [ ] `make test` passes, both locally and in CI.
- [ ] Each of the 3 classes produces `label.json` plus the real captured artefacts.
- [ ] The remaining 12 classes raise `NotImplementedError`.
- [ ] No fabricated logs. Every artefact is captured from a real run.

## Out of scope
- Anything inside cFS (the Docker image is Ben's task on `feat/cfs-docker-image`).
- Distractor noise, data splits and model inference.
