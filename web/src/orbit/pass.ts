import type { SatRec } from "satellite.js";
import { lookAnglesAt, satrecFromTle } from "./look";
import type { Station } from "./station";
import type { ParsedTle } from "./tle";

export type Pass = {
  rise: Date;
  set: Date;
  maxElDeg: number;
  maxElAt: Date;
};

const STEP_MS = 15_000;
const REFINE_MS = 1_000;
const SEARCH_MS = 36 * 60 * 60 * 1000;
const BACK_MS = 20 * 60 * 1000;

function elevation(satrec: SatRec, station: Station, ms: number): number | null {
  try {
    return lookAnglesAt(satrec, station, new Date(ms)).elevationDeg;
  } catch {
    return null;
  }
}

function above(
  satrec: SatRec,
  station: Station,
  ms: number,
  maskDeg: number,
): boolean {
  const el = elevation(satrec, station, ms);
  return el !== null && el >= maskDeg;
}

function refineEdge(
  satrec: SatRec,
  station: Station,
  lo: number,
  hi: number,
  maskDeg: number,
  findRise: boolean,
): number {
  while (hi - lo > REFINE_MS) {
    const mid = Math.floor((lo + hi) / 2);
    if (above(satrec, station, mid, maskDeg)) {
      if (findRise) {
        hi = mid;
      } else {
        lo = mid;
      }
    } else if (findRise) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return findRise ? hi : lo;
}

function peak(
  satrec: SatRec,
  station: Station,
  riseMs: number,
  setMs: number,
): { maxElDeg: number; maxElAt: Date } {
  let maxElDeg = -90;
  let maxElAtMs = riseMs;
  for (let t = riseMs; t <= setMs; t += REFINE_MS) {
    const el = elevation(satrec, station, t);
    if (el !== null && el > maxElDeg) {
      maxElDeg = el;
      maxElAtMs = t;
    }
  }
  return { maxElDeg, maxElAt: new Date(maxElAtMs) };
}

function completePass(
  satrec: SatRec,
  station: Station,
  insideMs: number,
  maskDeg: number,
): Pass | null {
  let riseLo = Math.max(insideMs - BACK_MS, insideMs - SEARCH_MS);
  while (riseLo < insideMs && above(satrec, station, riseLo, maskDeg)) {
    riseLo = Math.max(insideMs - SEARCH_MS, riseLo - BACK_MS);
  }
  if (above(satrec, station, riseLo, maskDeg)) {
    return null;
  }
  const rise = refineEdge(satrec, station, riseLo, insideMs, maskDeg, true);

  let setHi = insideMs + STEP_MS;
  const limit = insideMs + SEARCH_MS;
  while (setHi < limit && above(satrec, station, setHi, maskDeg)) {
    setHi += STEP_MS;
  }
  if (above(satrec, station, setHi, maskDeg)) {
    return null;
  }
  const set = refineEdge(satrec, station, insideMs, setHi, maskDeg, false);
  const { maxElDeg, maxElAt } = peak(satrec, station, rise, set);
  return {
    rise: new Date(rise),
    set: new Date(set),
    maxElDeg,
    maxElAt,
  };
}

/**
 * Next contact window: time the satellite stays above `maskDeg` at the station.
 * If a pass is already in progress at `from`, that pass is returned.
 */
export function nextPass(
  tle: ParsedTle,
  station: Station,
  from: Date,
  maskDeg: number,
): Pass | null {
  const satrec = satrecFromTle(tle);
  const start = from.getTime();
  if (above(satrec, station, start, maskDeg)) {
    return completePass(satrec, station, start, maskDeg);
  }
  const end = start + SEARCH_MS;
  let prev = start;
  for (let t = start + STEP_MS; t <= end; t += STEP_MS) {
    if (above(satrec, station, t, maskDeg)) {
      const rise = refineEdge(satrec, station, prev, t, maskDeg, true);
      return completePass(satrec, station, rise + REFINE_MS, maskDeg);
    }
    prev = t;
  }
  return null;
}
