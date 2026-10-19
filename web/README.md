# OrbitLog web (v1)

Isolated Vite + React + TypeScript app. Needs Node ≥ 22.11. The Python benchmark does not depend on
Node. `make test` and `make reproduce` must work without this folder.

This app **only reads** benchmark outputs. It never computes or edits numbers.
Until `results/` exists, diagnosis UI is `pending`.

## Commands

```bash
cd web
npm install
npm run dev    # http://localhost:5173
npm test
```

From the repo root, `make test-web` runs `npm test` here. It is not part of
`make test`.

## Sprints

- 12: this scaffold
- 13: CelesTrak TLEs + SGP4
- 14: Nairobi contact windows
- 15: Cesium globe, picker, credits, Heavens-Above/N2YO check
