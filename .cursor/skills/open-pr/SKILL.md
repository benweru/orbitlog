---
name: open-pr
description: Commit, push and open a pull request in OrbitLog using the repo's naming conventions. Use whenever work is ready for review.
---

# Open a PR

Follow [AGENTS.md](../../../AGENTS.md).

1. Never push to `main`. Work on one branch for this task, named `type/goal-in-kebab-case` (types: feat, fix, chore, docs, test, refactor, perf, exp).
2. Commits use Conventional Commits: `type(optional-scope): short present-tense summary`, 72 characters or less. Add a body only when the reason isn't obvious.
3. Run `make test`. It must pass before you push.
4. `git push -u origin <branch>`, then `gh pr create -B main -t "<commit-style title>" -F <body file>`.
5. PR body:
   - **What and why**, and a link to the task brief in `docs/tasks/`
   - **How it was verified**: paste the **real** output from `make test`, the build and boot logs, or the generated results tables. Trim it if long, but never paraphrase or make up output.
   - **What's still missing or a known issue**
6. Don't merge your own PR. Ben reviews it. Don't push to branches owned by the other agent.
