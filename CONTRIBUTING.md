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

## CI
The workflow lives at `ci/test.yml` until it is moved to `.github/workflows/test.yml` (the bot token lacks `workflow` scope, so Ben adds it):
`mkdir -p .github/workflows && git mv ci/test.yml .github/workflows/test.yml`
