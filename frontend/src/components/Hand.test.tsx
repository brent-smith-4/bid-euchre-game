import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Card } from "../protocol";
import { Hand } from "./Hand";

const NINE_CLUBS: Card = { suit: "CLUBS", rank: "NINE" };
const ACE_HEARTS: Card = { suit: "HEARTS", rank: "ACE" };

describe("Hand", () => {
  it("renders every card as static (non-interactive) when it isn't your turn", () => {
    render(
      <Hand cards={[NINE_CLUBS, ACE_HEARTS]} yourTurn={false} legalPlays={[]} onPlay={vi.fn()} />,
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("greys out cards not in legal_plays and keeps legal ones clickable", () => {
    const onPlay = vi.fn();
    render(
      <Hand
        cards={[NINE_CLUBS, ACE_HEARTS]}
        yourTurn
        legalPlays={[ACE_HEARTS]}
        onPlay={onPlay}
      />,
    );

    const nineClubs = screen.getByRole("button", { name: /9 of clubs/i });
    const aceHearts = screen.getByRole("button", { name: /a of hearts/i });

    expect(nineClubs).toBeDisabled();
    expect(aceHearts).toBeEnabled();

    fireEvent.click(aceHearts);
    expect(onPlay).toHaveBeenCalledWith(ACE_HEARTS);
  });
});
