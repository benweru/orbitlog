/**
 * Convert SGP4’s ECI kilometres into geodetic lat/lon/height so Cesium can
 * place the satellite on the globe.
 */
import * as satellite from "satellite.js";
import { satrecFromTle } from "./look";
import { propagateEci } from "./sgp4";
import type { ParsedTle } from "./tle";

export type Lla = {
  latitudeDeg: number;
  longitudeDeg: number;
  heightKm: number;
};

export function eciToLla(eci: { x: number; y: number; z: number }, when: Date): Lla {
  const gd = satellite.eciToGeodetic(eci, satellite.gstime(when));
  return {
    latitudeDeg: satellite.degreesLat(gd.latitude),
    longitudeDeg: satellite.degreesLong(gd.longitude),
    heightKm: gd.height,
  };
}

export function llaAt(tle: ParsedTle, when: Date): Lla {
  return eciToLla(propagateEci(tle, when), when);
}

export function sampleTrack(
  tle: ParsedTle,
  from: Date,
  durationMs: number,
  stepMs: number,
): Lla[] {
  const satrec = satrecFromTle(tle);
  const out: Lla[] = [];
  for (let t = from.getTime(); t <= from.getTime() + durationMs; t += stepMs) {
    const when = new Date(t);
    const result = satellite.propagate(satrec, when);
    const position = result?.position;
    if (!position || typeof position.x !== "number") {
      continue;
    }
    out.push(eciToLla(position, when));
  }
  return out;
}
