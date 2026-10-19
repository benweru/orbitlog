# Sprint 15: Live globe, picker and credits

- **Sprint:** 15: Live globe, picker and credits *(title pending Ben's approval)*
- **Owner:** Ben's agent
- **Branch:** `feat/web-orbit-contact-windows`
- **PR title:** `feat(web): show a live satellite and Nairobi contact windows`

## Goal
v1 of the visualization: a CesiumJS globe with a real satellite moving on its SGP4 track, Nairobi marked, the next contact highlighted, a few satellites to pick, and credits. Pass times agree with an independent source to about a minute.

## Context
Closes the v1 acceptance list in the visualization brief. Use CesiumJS (or Resium) plus the sprint 13–14 libraries. Official Vite asset wiring: copy Workers/ThirdParty/Assets/Widgets and set `CESIUM_BASE_URL` ([Cesium + Vite](https://cesium.com/blog/2024/02/13/configuring-vite-or-webpack-for-cesiumjs/)). Prefer OSM / Ion-optional imagery so the app runs without a paid token; if `VITE_CESIUM_ION_TOKEN` is set, use it.

Satellites: ISS 25544, Landsat 9 49260, plus the CubeSat CATNR chosen in sprint 13.

Honesty: no diagnosis numbers. Any v2 panel is **pending**. Faults are not shown.

## Steps
1. Pin `cesium` (and Resium only if it earns its keep). Wire static assets.
2. Viewer: Earth, Nairobi point, satellite entity updated from SGP4, orbit polyline, next-pass arc highlighted.
3. HUD: countdown, rise / max el / set, TLE fetch time, elevation mask, satellite picker.
4. In-app credits: CelesTrak, Cesium, imagery provider, satellite.js; mention Skyhitch / God's Eye View as inspiration (MIT) without copying code.
5. Vitest stays on orbital math (already in 13–14). Do not try to unit-test WebGL.
6. **Verification (required in the PR):** ISS over Nairobi vs [Heavens-Above](https://heavens-above.com/) or [N2YO](https://www.n2yo.com/). Use the same mask those sites use (state it). Rise/set within **~1 minute**. Paste times, URLs, and a screenshot.

## Acceptance criteria
- [ ] `cd web && npm install && npm run dev` shows a real satellite moving.
- [ ] Next Nairobi pass (rise, max elevation, set) shown; independent check within ~1 min, recorded in the PR.
- [ ] Unit tests pass; load feels under ~5 s on a normal laptop (note machine in the PR).
- [ ] Credits visible in the app.
- [ ] `make test` (Python) still passes without Node.

## Out of scope
- v2: fault injection playback, byte comparison, downlink queue (needs committed `results/`).
- Any fabricated accuracy or byte figures.
