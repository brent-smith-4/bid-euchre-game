import { describe, expect, it } from "vitest";
import { relativeSeat } from "./seating";

describe("relativeSeat", () => {
  it("always places the viewer's own seat at bottom", () => {
    expect(relativeSeat(2, 2)).toBe("bottom");
  });

  it("places the next clockwise seat at left, matching turn order", () => {
    expect(relativeSeat(0, 1)).toBe("left");
  });

  it("places the partner (seat + 2) at top", () => {
    expect(relativeSeat(0, 2)).toBe("top");
  });

  it("places the previous clockwise seat at right", () => {
    expect(relativeSeat(0, 3)).toBe("right");
  });

  it("wraps around seat ids correctly for any viewer", () => {
    expect(relativeSeat(3, 0)).toBe("left");
    expect(relativeSeat(3, 1)).toBe("top");
    expect(relativeSeat(3, 2)).toBe("right");
  });
});
