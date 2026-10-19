import { describe, expect, it } from "vitest";
import issTle from "./fixtures/iss.tle?raw";
import { propagateEci, radiusKm } from "./sgp4";
import { parseTle } from "./tle";

describe("propagateEci", () => {
  it("puts ISS in LEO near the TLE epoch", () => {
    const tle = parseTle(issTle);
    // Epoch on line 1 is year 26, day 292.43498098 UTC ≈ 2026-10-19.
    const when = new Date(Date.UTC(2026, 9, 19, 10, 26, 22));
    const eci = propagateEci(tle, when);
    const r = radiusKm(eci);
    expect(r).toBeGreaterThan(6500);
    expect(r).toBeLessThan(7000);
  });
});
