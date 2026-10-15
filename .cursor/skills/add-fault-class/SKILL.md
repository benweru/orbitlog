---
name: add-fault-class
description: Add or implement a fault class in OrbitLog's injector. Use when adding a new fault type, changing configs/fault_classes.yaml, or implementing an injector in src/orbitlog/faults/.
---

# Add a fault class

Follow [AGENTS.md](../../../AGENTS.md). The background is in docs/plan.md, section 4.

1. Branch: `feat/fault-<class-name>` (for example `feat/fault-disk-full`).
2. Config: add the class to `configs/fault_classes.yaml` (or confirm it's there) with a unique `id`, a snake_case `name` and a `description`. Update the class-count test if the total changes.
3. Injector: subclass `FaultInjector` in `src/orbitlog/faults/` and register it under the YAML `name`.
   - `prepare(seed)`: work out every parameter from the seed and nothing else, so it's deterministic.
   - Build the label `{fault_class, component, injected_param, timestamp (UTC), seed, trigger_status}`. **Write `label.json` and fsync it BEFORE `trigger()`.** If triggering fails, keep the label and set `trigger_status: failed`. Never relabel after the fact.
   - `collect(out_dir)`: copy in only the real artefacts (logs, dmesg, traces). Never write synthetic log text.
   - `cleanup()`: restore the system state.
4. Test in `tests/`: the label exists before trigger (use a mock trigger), the schema is valid, the same seed gives the same parameters, and an end-to-end run works in `tmp_path`.
5. Leave other unimplemented classes as stubs that raise `NotImplementedError`.
6. Run `make test`. Commit as `feat(faults): add <class> injector`, then use the open-pr skill.
