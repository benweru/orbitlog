import { describe, expect, it } from "vitest";
import issTle from "./fixtures/iss.tle?raw";
import { fetchAndCacheTle } from "./fetchTle";

describe("fetchAndCacheTle", () => {
  it("parses a mocked CelesTrak body and stores fetchedAt", async () => {
    const fetchImpl: typeof fetch = async () =>
      new Response(issTle, { status: 200 });
    const entry = await fetchAndCacheTle(
      25544,
      new Date("2026-10-19T22:05:00.000Z"),
      fetchImpl,
    );
    expect(entry.name).toBe("ISS (ZARYA)");
    expect(entry.fetchedAt).toBe("2026-10-19T22:05:00.000Z");
  });
});
