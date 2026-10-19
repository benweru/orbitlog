/**
 * A TLE (two-line element set) is a snapshot of an orbit at one epoch:
 * two 69-character lines (plus an optional name line) published by CelesTrak.
 *
 * SGP4, used in sgp4.ts, is the standard propagator that turns those lines
 * into a position. A TLE is good for days, not months.
 *
 * Always pass FORMAT=TLE. On 2026-05-09 CelesTrak’s default GP format became CSV
 * (https://celestrak.org/NORAD/documentation/gp-data-formats.php).
 */

export const CELESTRAK_GP =
  "https://celestrak.org/NORAD/elements/gp.php";

export type ParsedTle = {
  name: string;
  line1: string;
  line2: string;
};

export function gpTleUrl(catnr: number): string {
  if (!Number.isInteger(catnr) || catnr <= 0) {
    throw new Error(`CATNR must be a positive integer, got ${catnr}`);
  }
  return `${CELESTRAK_GP}?CATNR=${catnr}&FORMAT=TLE`;
}

/** Dev goes through the Vite proxy so the browser does not hit CelesTrak CORS. */
export function browserGpTleUrl(catnr: number): string {
  if (import.meta.env.DEV) {
    return `/api/celestrak/gp.php?CATNR=${catnr}&FORMAT=TLE`;
  }
  return gpTleUrl(catnr);
}

export function parseTle(text: string): ParsedTle {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter((line) => line.trim().length > 0);
  if (lines.length < 2) {
    throw new Error("TLE is truncated: need two element lines");
  }

  let name = "UNKNOWN";
  let line1: string;
  let line2: string;
  if (lines[0].startsWith("1 ") && lines[1].startsWith("2 ")) {
    line1 = lines[0];
    line2 = lines[1];
  } else if (
    lines.length >= 3 &&
    lines[1].startsWith("1 ") &&
    lines[2].startsWith("2 ")
  ) {
    name = lines[0].trim();
    line1 = lines[1];
    line2 = lines[2];
  } else {
    throw new Error("TLE is truncated or not two-line format");
  }

  if (line1.length !== 69 || line2.length !== 69) {
    throw new Error(
      `TLE lines must be 69 characters (got ${line1.length} and ${line2.length})`,
    );
  }
  return { name, line1, line2 };
}
