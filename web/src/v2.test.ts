import { describe, expect, it } from "vitest";
import { V2_STATUS } from "./v2";

describe("v2 diagnosis panel", () => {
  it("stays pending until committed results exist", () => {
    expect(V2_STATUS).toBe("pending");
  });
});
