import { describe, expect, it } from "vitest";
import { describeError } from "./protocol";

describe("describeError", () => {
  it("maps the follow-suit error to the specific player-facing copy", () => {
    expect(describeError("must follow suit")).toBe("You must follow suit!");
  });

  it("maps out-of-turn bid/play errors to a generic turn message", () => {
    expect(describeError("not player 2's turn to bid")).toBe("It's not your turn yet.");
    expect(describeError("not player 0's turn to play")).toBe("It's not your turn yet.");
  });

  it("maps illegal bid errors to a generic bid message", () => {
    expect(describeError("illegal bid SIX")).toBe("That bid isn't legal right now.");
  });

  it("falls back to the raw message for unmapped errors", () => {
    expect(describeError("something unexpected")).toBe("something unexpected");
  });
});
