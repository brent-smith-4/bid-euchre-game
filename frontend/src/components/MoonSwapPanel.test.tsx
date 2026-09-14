import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Card } from "../protocol";
import { MoonSwapPanel } from "./MoonSwapPanel";

const HAND: Card[] = [
  { suit: "CLUBS", rank: "NINE" },
  { suit: "HEARTS", rank: "ACE" },
];

describe("MoonSwapPanel", () => {
  it("shows a bidder-specific waiting message when it isn't your turn and you're the bidder", () => {
    render(
      <MoonSwapPanel isYourTurn={false} isBidder yourHand={HAND} onSubmitSwapCard={vi.fn()} />,
    );
    expect(screen.getByText(/waiting for your partner/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirm/i })).not.toBeInTheDocument();
  });

  it("shows a generic waiting message for everyone else", () => {
    render(
      <MoonSwapPanel isYourTurn={false} isBidder={false} yourHand={HAND} onSubmitSwapCard={vi.fn()} />,
    );
    expect(screen.getByText(/waiting for the shoot-the-moon/i)).toBeInTheDocument();
  });

  it("lets the partner pick a card and submit it, disabled until one is chosen", () => {
    const onSubmitSwapCard = vi.fn();
    render(
      <MoonSwapPanel isYourTurn isBidder={false} yourHand={HAND} onSubmitSwapCard={onSubmitSwapCard} />,
    );

    const confirmButton = screen.getByRole("button", { name: /confirm/i });
    expect(confirmButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /a of hearts/i }));
    expect(confirmButton).toBeEnabled();

    fireEvent.click(confirmButton);
    expect(onSubmitSwapCard).toHaveBeenCalledWith(HAND[1]);
  });

  it("lets you switch your pick to a different card instead of being locked in", () => {
    const onSubmitSwapCard = vi.fn();
    render(
      <MoonSwapPanel isYourTurn isBidder={false} yourHand={HAND} onSubmitSwapCard={onSubmitSwapCard} />,
    );

    const firstCard = screen.getByRole("button", { name: /9 of clubs/i });
    const secondCard = screen.getByRole("button", { name: /a of hearts/i });

    fireEvent.click(firstCard);
    expect(firstCard).toBeEnabled();
    expect(secondCard).toBeEnabled(); // not disabled just because another card is selected

    fireEvent.click(secondCard);
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onSubmitSwapCard).toHaveBeenCalledWith(HAND[1]);
  });

  it("lets you unselect a card by clicking it again, disabling confirm", () => {
    render(
      <MoonSwapPanel isYourTurn isBidder={false} yourHand={HAND} onSubmitSwapCard={vi.fn()} />,
    );

    const card = screen.getByRole("button", { name: /9 of clubs/i });
    fireEvent.click(card);
    expect(screen.getByRole("button", { name: /confirm/i })).toBeEnabled();

    fireEvent.click(card);
    expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
  });
});
