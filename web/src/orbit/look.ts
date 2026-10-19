/**
 * Look angles are how a ground station sees a satellite: azimuth (compass
 * direction, 0° = north), elevation (angle above the horizon), and range.
 *
 * A contact window is the stretch of time elevation stays above the mask.
 */
import * as satellite from "satellite.js";
import type { SatRec } from "satellite.js";
import type { Station } from "./station";
import type { ParsedTle } from "./tle";

export type LookAngles = {
  azimuthDeg: number;
  elevationDeg: number;
  rangeKm: number;
};

export function satrecFromTle(tle: ParsedTle): SatRec {
  return satellite.twoline2satrec(tle.line1, tle.line2);
}

export function lookAnglesAt(
  satrec: SatRec,
  station: Station,
  when: Date,
): LookAngles {
  const result = satellite.propagate(satrec, when);
  const position = result?.position;
  if (
    position === undefined ||
    position === null ||
    typeof position.x !== "number"
  ) {
    throw new Error("SGP4 did not return a position");
  }
  const gmst = satellite.gstime(when);
  const ecf = satellite.eciToEcf(position, gmst);
  const observer = {
    latitude: satellite.degreesToRadians(station.latitudeDeg),
    longitude: satellite.degreesToRadians(station.longitudeDeg),
    height: station.heightKm,
  };
  const look = satellite.ecfToLookAngles(observer, ecf);
  return {
    azimuthDeg: satellite.radiansToDegrees(look.azimuth),
    elevationDeg: satellite.radiansToDegrees(look.elevation),
    rangeKm: look.rangeSat,
  };
}

export function lookAngles(
  tle: ParsedTle,
  station: Station,
  when: Date,
): LookAngles {
  return lookAnglesAt(satrecFromTle(tle), station, when);
}
