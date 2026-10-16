# Contributing

OrbitLog is built by two contributors who each work locally:

- **Ben** builds on his own machine.
- **The bot** (Grok Bot) builds on its own machine (the box). It does not use cloud agents.

The repo is the only shared surface.

## Workflow
1. Branch from an up-to-date `main`: `git switch main && git pull && git switch -c <who>/<topic>` (e.g. `ben/cfs-docker`, `bot/memory-harness`).
2. Keep commits small. Run `make test` before pushing.
3. Open a PR to `main`. CI runs `make test`; the other contributor reviews.
4. Ben approves merges to `main`. The initial scaffold was the only direct push.

## Rules
- No fabricated results: stubs raise `NotImplementedError` until they're real.
- Never commit models, `data/raw/` or virtualenvs (see `.gitignore`).
- Pin dependency versions in `pyproject.toml` and `requirements*.txt`.
- Scripts call `python` (the Makefile uses `PYTHON ?= python`).
- Results must log a hardware and kernel fingerprint.

## Naming conventions

### Branches: `type/goal-in-kebab-case`
The name says what the branch is for. Never use generic names like `phase-1`, `wip` or `ben-stuff`.
- `feat/cfs-docker-image`
- `feat/fault-injector-core`
- `fix/cgroup-peak-memory-reading`
- `exp/e2b-iq2-quant-grid`
- `docs/plan-weeks-to-sprints`

### Commits: Conventional Commits
`type(optional-scope): short present-tense summary`, 72 characters or less. Add a body only when the reason isn't obvious.
- `feat(cfs): add Dockerfile pinned to cFS v7.0.1`
- `fix(memory): read memory.peak from the scope cgroup`
- `exp(e1): run Q4_0 vs IQ2_M at 512 MiB on 60 test cases`
- `docs(tasks): add sprint 3 linux-fault-injection brief`

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `exp` (benchmark and experiment runs).
Branches use a slash (`feat/...`) and commits use a colon (`feat: ...`). PR titles follow the commit style.
