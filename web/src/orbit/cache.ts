import type { ParsedTle } from "./tle";

export type CachedTle = ParsedTle & {
  catnr: number;
  fetchedAt: string;
};

const KEY = "orbitlog.tle.v1";

export function makeTleCache(storage: Storage) {
  function readAll(): Record<string, CachedTle> {
    const raw = storage.getItem(KEY);
    if (!raw) {
      return {};
    }
    try {
      const parsed: unknown = JSON.parse(raw);
      if (parsed !== null && typeof parsed === "object") {
        return parsed as Record<string, CachedTle>;
      }
    } catch {
      storage.removeItem(KEY);
    }
    return {};
  }

  function writeAll(all: Record<string, CachedTle>): void {
    storage.setItem(KEY, JSON.stringify(all));
  }

  return {
    get(catnr: number): CachedTle | undefined {
      return readAll()[String(catnr)];
    },
    put(catnr: number, tle: ParsedTle, fetchedAt: Date): CachedTle {
      const entry: CachedTle = {
        catnr,
        name: tle.name,
        line1: tle.line1,
        line2: tle.line2,
        fetchedAt: fetchedAt.toISOString(),
      };
      const all = readAll();
      all[String(catnr)] = entry;
      writeAll(all);
      return entry;
    },
  };
}

export function tleCache(): ReturnType<typeof makeTleCache> {
  return makeTleCache(window.localStorage);
}
