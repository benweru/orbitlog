import { describe, expect, it } from "vitest";
import issTle from "./fixtures/iss.tle?raw";
import { gpTleUrl, parseTle } from "./tle";

describe("parseTle", () => {
  it("reads a 3-line CelesTrak TLE", () => {
    const tle = parseTle(issTle);
    expect(tle.name).toBe("ISS (ZARYA)");
    expect(tle.line1.startsWith("1 25544")).toBe(true);
    expect(tle.line2.startsWith("2 25544")).toBe(true);
    expect(tle.line1).toHaveLength(69);
    expect(tle.line2).toHaveLength(69);
  });

  it("rejects truncated text", () => {
    expect(() => parseTle("ISS (ZARYA)\n1 25544U")).toThrow(/truncated/);
  });
});

describe("gpTleUrl", () => {
  it("forces FORMAT=TLE", () => {
    expect(gpTleUrl(25544)).toBe(
      "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE",
    );
  });
});
