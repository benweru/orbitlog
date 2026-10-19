# Sprint 12: Isolated Vite globe shell

- **Sprint:** 12: Isolated Vite globe shell *(title pending Ben's approval)*
- **Owner:** Ben's agent
- **Branch:** `feat/web-vite-scaffold`
- **PR title:** `feat(web): add isolated Vite React TypeScript app`

## Goal
A `web/` app with its own `package.json` that installs and runs without touching the Python benchmark. `make test` and `make reproduce` still work with no Node.

## Context
The visualization brief (`web-agent-brief-visualisation`) is v1 first: a Cesium globe later; this sprint only proves the Node island. Stack: Vite + React + TypeScript + Vitest. Pin exact npm versions. Inspired by [Skyhitch](https://skyhitch.app/) / [God's Eye View](https://github.com/bilawalsidhu/gods-eye-view) (MIT), but this PR does not copy their code.

Cesium stays out of this sprint so CI stays light and the globe work is one PR (`feat/web-orbit-contact-windows` in sprint 15).

## Steps
1. Scaffold `web/` (Vite React-TS). Pin versions. Add Vitest with one smoke test.
2. Root `.gitignore`: `web/node_modules/`, `web/dist/`.
3. `web/README.md`: `npm install`, `npm run dev`, `npm test`. State that this app never computes benchmark numbers.
4. Placeholder page: what OrbitLog is, that v1 will show real orbits, that diagnosis UI is v2 and **pending** until `results/` exists. No fake figures.
5. Optional `make test-web` that runs `npm test` in `web/`. Do **not** fold it into `make test`.
6. GitHub Actions: a `web` job on PRs that touch `web/**`, using Node 22 (matches the local toolchain used to pin packages).

## Acceptance criteria
- [ ] `cd web && npm install && npm run dev` serves the placeholder.
- [ ] `cd web && npm test` passes.
- [ ] `make test` still runs pytest only (no Node).
- [ ] `make test` passes locally and in CI.

## Out of scope
- Cesium, TLEs, SGP4, pass prediction (sprints 13–15).
- Anything under `src/orbitlog/` or `results/`.
