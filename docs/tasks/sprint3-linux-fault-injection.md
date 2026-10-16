# Sprint 3: Linux-side fault injection

- **Owner:** Ben's agent
- **Branch:** `feat/fault-oom-alloc-and-i2c-nack`
- **PR title:** `feat(faults): add oom_alloc_failure and i2c_sensor_nack injectors`

## Goal
Two more registered fault classes (ids 1 and 2 in `configs/fault_classes.yaml`) that reproduce the two scenarios Satlyt published, with real artefacts and ground-truth labels written before trigger.

## Context
- docs/plan.md §8 schedules this phase as "All 15 classes, noise, split". §4 lists "OOM/allocation failure" and "I2C/sensor NACK (simulated by unbinding the driver or using a fake i2c-stub device)". **Gap:** the plan names neither class for this sprint specifically and doesn't define their parameters or artefacts. This brief takes both from the article below.
- Satlyt case study (checked 16 Oct 2026, https://deepmind.google/models/gemma/gemmaverse/satlyt/). The same details appear in Ben's background notes (`orbitlog-context.md` §1, kept out of the repo):
  - **OOM:** "telemetry snapshot showing 99.6% RAM utilization and a system log indicating an OutOfMemoryError: Failed to allocate 144000000 bytes from the OpenCV preprocessing script when attempting to load a 12000x12000 image".
  - **Sensor:** "a kernel warning: tegra-i2c 3180000.i2c: no acknowledge from address 0x36 and an OSError: [Errno 121] Remote I/O error triggered during a scheduled camera payload capture". Target hardware is a Jetson Orin Nano.
- **What this machine supports** (probed 16 Oct 2026, Windows 11 + Docker Desktop, VM kernel `6.6.87.2-microsoft-standard-WSL2`):
  - cgroup v2 memory caps work. With `--memory=64m --memory-swap=64m`, a 12000×12000×1 allocation got exit 137 with `oom_kill 1` in `memory.events`. Under `ulimit -v 98304` it raised `MemoryError` at `bytearray(n)`.
  - The kernel config has `CONFIG_I2C=y` and `CONFIG_I2C_CHARDEV=m`, but **no `CONFIG_I2C_STUB`**, and containers have no `/lib/modules`. **So `i2c_sensor_nack` cannot be triggered here.** It needs a Linux host with the `i2c-stub` module (for example the Pi in plan §9).
- Kernel interfaces: `i2c-stub` takes `chip_addr` (up to 10) and answers SMBus commands only at those addresses (https://docs.kernel.org/i2c/i2c-stub.html). `/dev/i2c-N` needs `i2c-dev`, with `ioctl(I2C_SLAVE, addr)` then SMBus transfers via `I2C_SMBUS` (https://docs.kernel.org/i2c/dev-interface.html).
- No OpenCV dependency: the loader is stdlib Python, so the error text is Python's `MemoryError` or a kernel OOM kill, not OpenCV's `OutOfMemoryError`. That difference is stated, not hidden.

## Steps
1. **`oom_alloc_failure`** (component `payload.preprocess`) runs in `python:3.13-slim`, pinned by digest, under a cgroup v2 cap with swap off.
   - Seeded parameters: frame size, which includes the article's 12000×12000×1; the cap in MiB; and the mode, either `rlimit_as` (in-process `MemoryError` traceback) or `cgroup_oom_kill` (exit 137).
   - Artefacts: real stdout and stderr, plus the container's `memory.events`, `memory.peak` and `memory.max`.
   - The trigger fails unless `MemoryError` or `oom_kill ≥ 1` is actually observed.
2. **`i2c_sensor_nack`** (component `payload.camera`) is Linux and root only.
   - Load `i2c-dev` and `i2c-stub chip_addr=<decoy>`. A camera-capture subprocess then does an SMBus read at a seeded sensor address that has no stub chip (0x36 is included).
   - Artefacts: its real traceback and the `dmesg` lines from the window.
   - The trigger fails unless the read raises `OSError`. Record the errno that actually occurs; don't assume 121.
   - Without the module or root, the trigger raises and the label stays `failed`.
   - Until it has a reliable real trigger it is **not registered by default**, following the policy applied to `sb_pipe_full`. It is enabled only by `ORBITLOG_ENABLE_I2C_STUB=1` on a Linux host.
3. Register both, update the class-count tests, and add unit tests with the add-fault-class checks: label before trigger, schema, seed determinism, and end to end in `tmp_path`.
4. Live tests carry a `docker` marker (OOM) or a `linux_i2c` marker (I2C) and are deselected by default.

## Acceptance criteria
- [ ] Real OOM trigger output for both modes pasted into the PR, with the hardware and kernel fingerprint.
- [ ] `i2c_sensor_nack` either has real trigger output from a Linux host with `i2c-stub`, or the PR states plainly that it hasn't run anywhere yet.
- [ ] `make test` passes. Nothing synthetic is written as log text.

## Out of scope
- The remaining 9 classes, distractor noise, the train/dev/test split and no-fault cases (later Sprint 3 tasks).
- Telemetry beyond the cgroup counters (for example a "99.6% RAM" snapshot): no telemetry collector exists yet.
