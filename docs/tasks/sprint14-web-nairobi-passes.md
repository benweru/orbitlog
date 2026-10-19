# Sprint 14: Nairobi contact windows

- **Sprint:** 14: Nairobi contact windows *(title pending Ben's approval)*
- **Owner:** Ben's agent
- **Branch:** `feat/web-nairobi-passes`
- **PR title:** `feat(web): predict Nairobi contact windows from look angles`

## Goal
Given a TLE and “now”, compute the next pass over Nairobi: rise time, max elevation, set time, and a live countdown. Pure functions, fully unit-tested. The globe still comes in sprint 15.

## Context
A **contact window** is the stretch of time the satellite is above a minimum elevation at the ground station. **Look angles** are azimuth (compass direction) and elevation (angle above the horizon) from that station to the satellite.

**Nairobi station** (city, not a specific dish), WGS-84:
- latitude **−1.286389°**, longitude **36.817223°** (1°17′11″S, 36°49′02″E, [Wikipedia: Nairobi](https://en.wikipedia.org/wiki/Nairobi))
- altitude **1795 m** (same article, elevation of the city)

**Elevation mask:** default **10°** (a typical “usable pass” cut, and the usual Heavens-Above default). Also compute **0°** internally so the Heavens-Above / N2YO comparison in sprint 15 can match their horizon setting. Document the mask in the UI.

`satellite.gstime` + `eciToEcf` + `ecfToLookAngles` in `satellite.js` give azimuth/elevation. A pass is a contiguous run of samples with elevation ≥ mask.

OrbitLog’s story: windows are about 5–10 minutes, a few times a day. Do not invent byte counts here.

## Steps
1. `lookAngles(tle, station, date)` → az, el, range.
2. `nextPass(tle, station, from, maskDeg)` → `{ rise, maxEl, maxElAt, set }` or none in the search window (search ≥ 24 h, 1 s or better near crossings).
3. `countdown(to, now)` → remaining seconds (clamp at 0).
4. Vitest with the sprint 13 ISS fixture: a known-in-test pass (freeze `now`); countdown arithmetic; mask 10° vs 0° changes rise/set.
5. Placeholder UI: next ISS pass over Nairobi (rise, max el, set, countdown) once a TLE is cached.

## Acceptance criteria
- [ ] Unit tests pass with no network.
- [ ] UI shows rise, max elevation, set, countdown, elevation mask, and TLE epoch/fetch time.
- [ ] `make test` (Python) still passes without Node.

## Out of scope
- Independent Heavens-Above / N2YO check (sprint 15 PR, needs the live globe and a dated screenshot).
- Cesium rendering, satellite picker.
- v2 diagnosis panels (show **pending** if anything is sketched).
