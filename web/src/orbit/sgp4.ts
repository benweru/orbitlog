/**
 * SGP4 (Simplified General Perturbations 4) is the model behind almost every
 * hobbyist and many operational “where is that satellite now?” tools.
 * `satellite.js` implements it. Input: a TLE. Output: kilometres in ECI
 * (Earth-centred inertial) coordinates at a UTC instant.
 */
import * as satellite from "satellite.js";
import type { ParsedTle } from "./tle";

export type EciKm = {
  x: number;
  y: number;
  z: number;
};

export function propagateEci(tle: ParsedTle, when: Date): EciKm {
  const satrec = satellite.twoline2satrec(tle.line1, tle.line2);
  const result = satellite.propagate(satrec, when);
  const position = result?.position;
  if (
    position === undefined ||
    position === null ||
    typeof position.x !== "number" ||
    typeof position.y !== "number" ||
    typeof position.z !== "number"
  ) {
    throw new Error("SGP4 did not return a position (TLE too old or malformed)");
  }
  return { x: position.x, y: position.y, z: position.z };
}

/** Distance from Earth’s centre, km. LEO is roughly 6,600–8,400 km. */
export function radiusKm(eci: EciKm): number {
  return Math.hypot(eci.x, eci.y, eci.z);
}
