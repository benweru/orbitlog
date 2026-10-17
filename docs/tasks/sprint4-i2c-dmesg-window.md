# Sprint 4: Fix the i2c_sensor_nack kernel-log window

- **Sprint:** 4: Dataset v1, noise and split (approved by Ben)
- **Owner:** Ben's agent
- **Branch:** `fix/i2c-dmesg-window`
- **PR title:** `fix(faults): cut the i2c dmesg window by kernel timestamp`

## Goal
`i2c_sensor_nack` writes a `dmesg.txt` that holds every kernel line produced during the trigger, however full the kernel log is. Dataset v1 needs these logs to be reliable.

## Context
- Found 17 Oct 2026 (PR #11): across 8 seeds `dmesg.txt` held 0 or 1 lines, and the counts changed between runs of the same seeds.
- Cause: `I2cSensorNack.trigger()` takes `before = len(_dmesg())` and later keeps `_dmesg()[before:]`. The kernel log is a fixed-size ring buffer (`CONFIG_LOG_BUF_SHIFT`, 256 KiB by default; check `dmesg | head -1` for the oldest line kept). Once it is full, old lines are evicted as new ones arrive, so the line count stops growing and the slice drops lines. A WSL2 VM shares one kernel log with Docker Desktop, so it fills during a long session.
- Reproduced on the real machine (`6.6.87.2-microsoft-standard-WSL2`): on a fresh VM (548 lines) a count slice and a timestamp slice both returned 2 lines per cycle. After filling the ring with 4000 labelled test lines (oldest kept: line 1816), the count slice returned 1 line where the timestamp slice returned 2. The test flood is test-only and never enters a dataset.
- `dmesg` prefixes each line with a monotonic `[seconds.microseconds]` timestamp. Source: util-linux `dmesg(1)`.

## Steps
1. Replace the line-count slice with a helper that returns the lines newer than the last timestamp seen before the trigger. Lines with the same timestamp as that last line are kept only if they weren't already in the earlier snapshot. Continuation lines without a timestamp follow the line before them.
2. Unit tests with fixed input lists (a parser test, not log data for the dataset): normal growth, ring eviction with the same length, equal timestamps, empty snapshot.
3. A live check on Linux with `i2c-stub`: fill the ring, run `i2c_sensor_nack`, and show `dmesg.txt` is non-empty for every seed.
4. Correct `docs/linux-fault-hosts.md`: replace the known-issue note with the cause and the fix. Also record that WSL2 mounts its own modules disk over `/lib/modules/<kernel>` on start, which hides the copied `i2c-*.ko` files, so the copy and `depmod -a` step must be repeated after each WSL restart.
5. Mark the Sprint 4 title approved in `docs/plan.md`.

## Acceptance criteria
- [ ] `dmesg.txt` is correct with a full ring buffer, shown with real output before and after the change.
- [ ] `make test` passes.
- [ ] Real logs pasted into the PR.

## Out of scope
- Reproducing the article's Errno 121 and its `no acknowledge` kernel line (not possible with `i2c-stub`).
- The remaining fault classes, distractor noise and the split (other Sprint 4 tasks).
