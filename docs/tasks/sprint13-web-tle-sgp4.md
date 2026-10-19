# Sprint 13: TLE cache and SGP4

- **Sprint:** 13: TLE cache and SGP4 *(title pending Ben's approval)*
- **Owner:** Ben's agent
- **Branch:** `feat/web-tle-sgp4`
- **PR title:** `feat(web): fetch CelesTrak TLEs and propagate with SGP4`

## Goal
The web app can load a Two-Line Element set (TLE) from CelesTrak, cache it with the fetch time, and turn it into a position at a given UTC instant using SGP4 (`satellite.js`). No globe yet.

## Context
Operators plan **contact windows** by propagating published TLEs with **SGP4**. CelesTrak GP queries are `https://celestrak.org/NORAD/elements/gp.php?{QUERY}=VALUE[&FORMAT=VALUE]` ([GP data formats](https://celestrak.org/NORAD/documentation/gp-data-formats.php)). `{QUERY}` must be uppercase. **Always pass `FORMAT=TLE`**: as of 2026-05-09 the default format is CSV, not TLE.

v1 catalog (fixed CATNRs, not a live group dump):
- ISS (ZARYA), CATNR **25544**
- LANDSAT 9 (Earth observation), CATNR **49260** ([SATCAT](https://en.wikipedia.org/wiki/Landsat_9))
- One CubeSat whose TLE still exists on CelesTrak `GROUP=cubesat` at implementation time (record the CATNR and a live fetch in the PR)

Comment in plain words: a TLE is a snapshot of an orbit; SGP4 is the standard propagator; it is good for days, not months.

## Steps
1. Depend on pinned `satellite.js`.
2. Fetch `gp.php?CATNR=<id>&FORMAT=TLE`, parse name + two lines, store in `localStorage` (or equivalent) with `fetchedAt` ISO UTC. Show fetch time in a small status line.
3. `propagateEci(tle, date)` using `satellite.twoline2satrec` + `satellite.propagate`.
4. Vitest: parse a **fixture** TLE (committed, not live-fetched in CI); reject truncated lines; cache round-trip including `fetchedAt`. Live CelesTrak is manual / documented in the PR, not required for CI.

## Acceptance criteria
- [ ] Unit tests pass with no network in CI.
- [ ] A live fetch of ISS 25544 is pasted into the PR (raw TLE + timestamp).
- [ ] UI (even the placeholder) shows TLE fetch time or “not fetched”.
- [ ] `make test` (Python) still passes without Node.

## Out of scope
- Look angles, Nairobi passes, Cesium (sprints 14–15).
- Diagnosis / `results/` (v2).
