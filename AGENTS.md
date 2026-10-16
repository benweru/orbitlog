# AGENTS.md

Rules for every coding agent in this repo: Ben's Cursor CLI agent and Grok Bot.

## Context
- Read `docs/plan.md` before starting any work.
- Task briefs live in `docs/tasks/`. Work only on the task you were given and stay inside its scope.

## Sprints
- Work is organized in sprints, not weeks. Each sprint has a title that Ben approves in chat. The schedule is in `docs/plan.md` section 8.
- When a sprint starts, propose a title in chat. Until Ben approves it, mark it *(title pending Ben's approval)* wherever it appears.
- Task briefs are named `docs/tasks/sprint<N>-<topic>.md`.

## Workflow
- One branch and one PR per task. **Never push directly to `main`.**
- Run `make test` before every push. It must pass.
- Ownership: branches created for Ben are owned by Ben's agent, and the bot does not touch them (no commits, rebases, force-pushes or reviews that change code). The bot works only on its own branches. Coordinate through PRs and comments.

## Naming
- Branches: `type/goal-in-kebab-case`, where the name states the goal (e.g. `feat/cfs-docker-image`, `fix/cgroup-peak-memory-reading`). Never generic names like `phase-1`.
- Commits: Conventional Commits, `type(optional-scope): short present-tense summary`, 72 characters or less, with a body only when the reason isn't obvious.
- Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `exp` (benchmark and experiment runs).
- Branches use a slash and commits use a colon. PR titles use the commit style.

## Code
- Use `python`, not `python3`, in scripts, docs and the Makefile (`PYTHON ?= python`).
- **Never fabricate results or benchmark numbers.** Every number must come from a run that is logged and can be reproduced, with a hardware and kernel fingerprint.
- Unimplemented code raises `NotImplementedError`. Never return placeholder data that looks real.
- Pin dependency versions. Never commit models, `data/raw/` or virtualenvs.

## Skills
Project skills for Cursor live in `.cursor/skills/`:
- `add-fault-class`: adding or implementing a fault class and its injector
- `run-experiment`: pinned, memory-capped benchmark runs with raw results
- `open-pr`: branch and commit conventions, test, then a PR with real logs
- `write-task-brief`: the template for `docs/tasks/` briefs
