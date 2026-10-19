import { describe, expect, it } from "vitest";
import { countdownSeconds, formatCountdown } from "./countdown";

describe("countdownSeconds", () => {
  it("clamps at zero", () => {
    const to = new Date("2026-10-19T12:00:00.000Z");
    const now = new Date("2026-10-19T12:00:10.000Z");
    expect(countdownSeconds(to, now)).toBe(0);
  });

  it("counts whole seconds remaining", () => {
    const to = new Date("2026-10-19T12:01:30.000Z");
    const now = new Date("2026-10-19T12:00:00.000Z");
    expect(countdownSeconds(to, now)).toBe(90);
  });
});

describe("formatCountdown", () => {
  it("formats mm:ss under an hour", () => {
    expect(formatCountdown(90)).toBe("01:30");
  });

  it("formats h:mm:ss over an hour", () => {
    expect(formatCountdown(3661)).toBe("1:01:01");
  });
});
