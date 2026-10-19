import { tleCache, type CachedTle } from "./cache";
import { browserGpTleUrl, parseTle } from "./tle";

export async function fetchAndCacheTle(
  catnr: number,
  now: Date = new Date(),
  fetchImpl: typeof fetch = fetch,
): Promise<CachedTle> {
  const response = await fetchImpl(browserGpTleUrl(catnr));
  if (!response.ok) {
    throw new Error(`CelesTrak HTTP ${response.status} for CATNR ${catnr}`);
  }
  const text = await response.text();
  const tle = parseTle(text);
  return tleCache().put(catnr, tle, now);
}
