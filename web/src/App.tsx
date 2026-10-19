import { useEffect, useMemo, useState } from "react";
import { tleCache, type CachedTle } from "./orbit/cache";
import { SATELLITES } from "./orbit/catalog";
import { countdownSeconds, formatCountdown } from "./orbit/countdown";
import { fetchAndCacheTle } from "./orbit/fetchTle";
import { nextPass, type Pass } from "./orbit/pass";
import { DEFAULT_ELEVATION_MASK_DEG, NAIROBI } from "./orbit/station";
import { V2_STATUS } from "./v2";

function utc(d: Date): string {
  return d.toISOString().replace(/\.\d{3}Z$/, "Z");
}

export default function App() {
  const [cached, setCached] = useState<Record<number, CachedTle>>({});
  const [selected, setSelected] = useState(SATELLITES[0].catnr);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [now, setNow] = useState(() => new Date());

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

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  async function load(catnr: number) {
    setBusy(catnr);
    setError(null);
    try {
      const entry = await fetchAndCacheTle(catnr);
      setCached((prev) => ({ ...prev, [catnr]: entry }));
      setSelected(catnr);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  const tle = cached[selected];
  const passBucket = Math.floor(now.getTime() / 15_000);
  const pass: Pass | null = useMemo(() => {
    if (!tle) {
      return null;
    }
    return nextPass(tle, NAIROBI, new Date(), DEFAULT_ELEVATION_MASK_DEG);
  }, [tle, passBucket]);

  const inPass =
    pass !== null &&
    now.getTime() >= pass.rise.getTime() &&
    now.getTime() < pass.set.getTime();

  return (
    <main>
      <p className="kicker">OrbitLog</p>
      <h1>Ride along with a real satellite and watch it think.</h1>
      <p>
        A <strong>contact window</strong> is the few minutes a satellite is
        above {DEFAULT_ELEVATION_MASK_DEG}° elevation at {NAIROBI.name}.{" "}
        <strong>Look angles</strong> are azimuth (compass direction) and
        elevation (angle above the horizon). The globe comes next.
      </p>
      <ul className="sats">
        {SATELLITES.map((sat) => {
          const hit = cached[sat.catnr];
          const active = sat.catnr === selected;
          return (
            <li key={sat.catnr} className={active ? "active" : undefined}>
              <button
                type="button"
                className="pick"
                onClick={() => setSelected(sat.catnr)}
              >
                {sat.name} <code>CATNR {sat.catnr}</code>
              </button>
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
      <section className="pass" aria-live="polite">
        <h2>
          Next pass over {NAIROBI.name} (mask {DEFAULT_ELEVATION_MASK_DEG}°)
        </h2>
        {!tle ? (
          <p>Fetch a TLE to predict the next window.</p>
        ) : !pass ? (
          <p>No pass in the next 36 hours for this TLE.</p>
        ) : (
          <dl>
            <dt>Countdown</dt>
            <dd>
              {inPass
                ? `In contact · sets in ${formatCountdown(countdownSeconds(pass.set, now))}`
                : formatCountdown(countdownSeconds(pass.rise, now))}
            </dd>
            <dt>Rise</dt>
            <dd>{utc(pass.rise)}</dd>
            <dt>Max elevation</dt>
            <dd>
              {pass.maxElDeg.toFixed(1)}° at {utc(pass.maxElAt)}
            </dd>
            <dt>Set</dt>
            <dd>{utc(pass.set)}</dd>
          </dl>
        )}
      </section>
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
