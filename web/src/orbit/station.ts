/**
 * Ground station: where we stand on Earth to wait for a contact window.
 * Coordinates are WGS-84 geodetic (the usual lat/lon/height).
 *
 * Nairobi city, not a specific dish:
 * 1°17′11″S, 36°49′02″E, elevation 1,795 m
 * https://en.wikipedia.org/wiki/Nairobi
 */
export type Station = {
  name: string;
  latitudeDeg: number;
  longitudeDeg: number;
  heightKm: number;
};

export const NAIROBI: Station = {
  name: "Nairobi",
  latitudeDeg: -1.286389,
  longitudeDeg: 36.817223,
  heightKm: 1.795,
};

/** Elevation mask: ignore the satellite until it is this many degrees up. */
export const DEFAULT_ELEVATION_MASK_DEG = 10;
