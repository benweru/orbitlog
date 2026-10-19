/**
 * v1 catalog: a few real objects we will plot.
 *
 * CATNR is the NORAD catalog number CelesTrak uses in
 * gp.php?CATNR=…&FORMAT=TLE (query key must be uppercase).
 */
export type SatelliteKind = "station" | "earth-observation" | "cubesat";

export type CatalogEntry = {
  catnr: number;
  name: string;
  kind: SatelliteKind;
};

export const SATELLITES: readonly CatalogEntry[] = [
  { catnr: 25544, name: "ISS (ZARYA)", kind: "station" },
  { catnr: 49260, name: "LANDSAT 9", kind: "earth-observation" },
  // CUTE-1 is Tokyo Tech’s 2003 CubeSat (CO-55). Still in CelesTrak GROUP=cubesat
  // with a fresh TLE as of 2026-10-19.
  { catnr: 27844, name: "CUTE-1 (CO-55)", kind: "cubesat" },
];
