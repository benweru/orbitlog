import { describe, expect, it } from "vitest";
import { makeTleCache } from "./cache";
import { parseTle } from "./tle";

const SAMPLE = `ISS (ZARYA)
1 25544U 98067A   26292.43498098  .00007189  00000-0  13878-3 0  9990
2 25544  51.6326  45.2419 0006754 282.9887  77.0347 15.48939196591015
`;

describe("tle cache", () => {
  it("round-trips a TLE and fetchedAt", () => {
    const cache = makeTleCache(window.localStorage);
    const tle = parseTle(SAMPLE);
    const fetchedAt = new Date("2026-10-19T22:00:00.000Z");
    const stored = cache.put(25544, tle, fetchedAt);
    expect(stored.fetchedAt).toBe("2026-10-19T22:00:00.000Z");
    expect(cache.get(25544)).toEqual(stored);
  });
});
