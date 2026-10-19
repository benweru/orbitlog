import { useEffect, useState } from "react";
import { SATELLITES } from "./orbit/catalog";
import { tleCache, type CachedTle } from "./orbit/cache";
import { fetchAndCacheTle } from "./orbit/fetchTle";
import { V2_STATUS } from "./v2";

export default function App() {
  const [cached, setCached] = useState<Record<number, CachedTle>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    const cache = tleCache();
    const next: Record<number, CachedTle> = {};
    for (const sat of SATELLITES) {
      const hit = cache.get(sat.catnr);
      if (hit) {
        next[sat.catnr] = hit;
      }
    }
    setCached(next);
  }, []);

  async function load(catnr: number) {
    setBusy(catnr);
    setError(null);
    try {
      const entry = await fetchAndCacheTle(catnr);
      setCached((prev) => ({ ...prev, [catnr]: entry }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main>
      <p className="kicker">OrbitLog</p>
      <h1>Ride along with a real satellite and watch it think.</h1>
      <p>
        A TLE is a snapshot of an orbit. SGP4 is the standard model that
        turns it into a position. Fetch times below are when this browser
        last pulled CelesTrak; the globe comes in a later sprint.
      </p>
      <ul className="sats">
        {SATELLITES.map((sat) => {
          const hit = cached[sat.catnr];
          return (
            <li key={sat.catnr}>
              <span>
                {sat.name}{" "}
                <code>CATNR {sat.catnr}</code>
              </span>
              <span className="meta">
                {hit ? `TLE fetched ${hit.fetchedAt}` : "TLE not fetched"}
              </span>
              <button
                type="button"
                disabled={busy === sat.catnr}
                onClick={() => void load(sat.catnr)}
              >
                {busy === sat.catnr ? "Fetching…" : "Fetch TLE"}
              </button>
            </li>
          );
        })}
      </ul>
      {error ? <p className="error">{error}</p> : null}
      <p>
        v2, the onboard diagnosis story, is <strong>{V2_STATUS}</strong> until
        the benchmark writes files under <code>results/</code>. This page will
        never invent those numbers.
      </p>
      <p className="note">
        Faults in OrbitLog are simulated on a ground Linux box, not live
        satellite telemetry. TLE data: CelesTrak.
      </p>
    </main>
  );
}
