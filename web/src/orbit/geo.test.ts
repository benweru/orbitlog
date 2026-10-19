import { describe, expect, it } from "vitest";
import issTle from "./fixtures/iss.tle?raw";
import { llaAt } from "./geo";
import { parseTle } from "./tle";

describe("llaAt", () => {
  it("keeps ISS within its 51.6° inclination band", () => {
    const tle = parseTle(issTle);
    const when = new Date(Date.UTC(2026, 9, 19, 10, 26, 22));
    const lla = llaAt(tle, when);
    expect(Math.abs(lla.latitudeDeg)).toBeLessThan(52);
    expect(lla.longitudeDeg).toBeGreaterThanOrEqual(-180);
    expect(lla.longitudeDeg).toBeLessThanOrEqual(180);
    expect(lla.heightKm).toBeGreaterThan(300);
    expect(lla.heightKm).toBeLessThan(500);
  });
});
