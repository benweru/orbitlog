# Sprint 1: NASA cFS in Docker

- **Sprint:** 1: Memory harness and cFS bring-up *(title pending Ben's approval)*
- **Owner:** Ben's agent
- **Branch:** `feat/cfs-docker-image`
- **PR title:** `feat(cfs): build and run cFS v7.0.1 in Docker`

## Goal
Build and boot the NASA cFS bundle (https://github.com/nasa/cFS) inside `docker/cfs/Dockerfile`, then add a Makefile target that starts it and streams its event messages. This is the system the fault injector will target.

## Pinned version
`v7.0.1`, the latest release ("cFS Bundle - v7.0.1", published 2026-05-14). Checked on GitHub on 2026-10-15. Pin the tag, not `main`.

## Facts checked against the cFS README at v7.0.1
- Requirements: Make, CMake, GCC, Git.
- Fetch the bundle: `git clone https://github.com/nasa/cFS.git`, then `git submodule init && git submodule update`.
- Build: `make native_std.prep`, then `make native_std.install`.
- Run: `cd build-native_std/exe/cpu1/ && ./core-cpu1`. The program must run from that directory to find its startup script and shared objects.
- Success signal: startup messages, then `CFE_ES_Main` entering the OPERATIONAL state.

## Steps
1. Replace the placeholder in `docker/cfs/Dockerfile`:
   - Base image `ubuntu:24.04`. Install `build-essential cmake git ca-certificates`.
   - Run `git clone --branch v7.0.1 --depth 1 https://github.com/nasa/cFS.git /cfs`, then `git submodule update --init --depth 1` (fall back to a full clone if a submodule fails to fetch at that depth).
   - Run `make native_std.prep && make native_std.install`. Skip `runtest` and `lcov`.
   - Set `WORKDIR /cfs/build-native_std/exe/cpu1` and `CMD ["./core-cpu1"]`.
   - Consider a multi-stage build so the runtime image stays small. This is optional.
2. Add Makefile targets (keep `PYTHON ?= python` untouched):
   - `cfs-build`: `docker build -t orbitlog-cfs docker/cfs`
   - `cfs-up`: run the container in the foreground, named `orbitlog-cfs`, removed on exit, so its event messages show on stdout. If message queues fail, the container may need `--ulimit msgqueue=...` or `--cap-add` options. Document whatever you add.
   - `cfs-logs` and `cfs-down` are optional.
3. Add a "cFS" section to `docker/README.md` covering the pinned tag, how to build and run, what the OPERATIONAL line looks like, and any known warnings (for example, the priority warnings you get when running as a non-root user).

## Acceptance criteria
- [ ] `docker build --no-cache -t orbitlog-cfs docker/cfs` succeeds from a clean state.
- [ ] `make cfs-up` boots cFS, and the logs show `CFE_ES_Main` entering OPERATIONAL.
- [ ] Event and startup messages appear in the terminal and through `docker logs`.
- [ ] `make test` still passes.
- [ ] The PR description pastes the real boot log excerpt. Do not paraphrase it or make it up.

## Out of scope
- Fault injection, labels and the dataset. Those are the bot's task in `sprint1-fault-injector.md` on `feat/fault-injector-core`.
- Ground-system tools (cFS-GroundSystem), telemetry decoding, EDS builds and RTEMS or cross-compile targets.
- CI for the Docker image. Running it in CI can be added later.
