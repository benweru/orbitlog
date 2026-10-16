---
name: write-task-brief
description: Write a task brief in docs/tasks/ for Ben's agent or the bot. Use when planning a new unit of work.
---

# Write a task brief

Follow [AGENTS.md](../../../AGENTS.md). Work is organized in titled sprints (docs/plan.md, section 8). Ben approves each sprint title in chat. If the sprint has no approved title yet, propose one in chat first, and mark it *(title pending Ben's approval)* in the brief until he approves it.

Save it as `docs/tasks/sprint<N>-<topic>.md`. Check every external fact (versions, commands, flags) against the source and cite it. Keep it to a page.

```markdown
# Sprint <N>: <Task title>

- **Sprint:** <N>: <sprint title> (approved by Ben | *title pending Ben's approval*)
- **Owner:** Ben's agent | Grok Bot
- **Branch:** `type/goal-in-kebab-case`
- **PR title:** `type(scope): summary`

## Goal
One or two sentences: what will exist when this is done.

## Context
Why it matters, with links to docs/plan.md sections and verified external facts (versions, sources).

## Steps
1. ...

## Acceptance criteria
- [ ] Concrete, checkable outcomes
- [ ] `make test` passes
- [ ] Real logs or results pasted into the PR

## Out of scope
- What is deliberately excluded, and who owns it
```

Commit as `docs(tasks): add sprint <N> <topic> brief`.
