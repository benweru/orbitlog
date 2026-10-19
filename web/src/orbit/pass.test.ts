import { describe, expect, it } from "vitest";
import issTle from "./fixtures/iss.tle?raw";
import { lookAngles } from "./look";
import { nextPass } from "./pass";
import { DEFAULT_ELEVATION_MASK_DEG, NAIROBI } from "./station";
import { parseTle } from "./tle";

const tle = parseTle(issTle);
const from = new Date(Date.UTC(2026, 9, 19, 10, 26, 22));

describe("lookAngles", () => {
  it("returns finite azimuth and elevation from Nairobi", () => {
    const look = lookAngles(tle, NAIROBI, from);
    expect(Number.isFinite(look.azimuthDeg)).toBe(true);
    expect(Number.isFinite(look.elevationDeg)).toBe(true);
    expect(look.azimuthDeg).toBeGreaterThanOrEqual(0);
    expect(look.azimuthDeg).toBeLessThan(360);
    expect(look.elevationDeg).toBeGreaterThan(-90);
    expect(look.elevationDeg).toBeLessThan(90);
  });
});

describe("nextPass", () => {
  it("finds a Nairobi ISS pass with rise, max elevation and set", () => {
    const pass = nextPass(tle, NAIROBI, from, DEFAULT_ELEVATION_MASK_DEG);
    expect(pass).not.toBeNull();
    if (!pass) {
      return;
    }
    expect(pass.rise.getTime()).toBeLessThanOrEqual(pass.maxElAt.getTime());
    expect(pass.maxElAt.getTime()).toBeLessThanOrEqual(pass.set.getTime());
    expect(pass.set.getTime()).toBeGreaterThan(pass.rise.getTime());
    expect(pass.maxElDeg).toBeGreaterThanOrEqual(DEFAULT_ELEVATION_MASK_DEG);
    const minutes = (pass.set.getTime() - pass.rise.getTime()) / 60_000;
    expect(minutes).toBeGreaterThan(1);
    expect(minutes).toBeLessThan(20);
    expect(lookAngles(tle, NAIROBI, pass.rise).elevationDeg).toBeGreaterThanOrEqual(
      DEFAULT_ELEVATION_MASK_DEG - 0.5,
    );
    expect(
      lookAngles(tle, NAIROBI, new Date(pass.rise.getTime() - 2000)).elevationDeg,
    ).toBeLessThan(DEFAULT_ELEVATION_MASK_DEG);
    expect(
      lookAngles(tle, NAIROBI, new Date(pass.set.getTime() + 2000)).elevationDeg,
    ).toBeLessThan(DEFAULT_ELEVATION_MASK_DEG);
  });

  it("treats 0° as a lower mask than 10° at the same 10° pass edges", () => {
    const high = nextPass(tle, NAIROBI, from, 10);
    expect(high).not.toBeNull();
    if (!high) {
      return;
    }
    const before = lookAngles(
      tle,
      NAIROBI,
      new Date(high.rise.getTime() - 2000),
    ).elevationDeg;
    const after = lookAngles(
      tle,
      NAIROBI,
      new Date(high.set.getTime() + 2000),
    ).elevationDeg;
    expect(before).toBeLessThan(10);
    expect(after).toBeLessThan(10);
    expect(before).toBeGreaterThan(-90);
  });
});
