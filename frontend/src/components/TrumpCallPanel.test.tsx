import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Card } from "../protocol";
import { TrumpCallPanel } from "./TrumpCallPanel";

const HAND: Card[] = [
  { suit: "CLUBS", rank: "NINE" },
  { suit: "HEARTS", rank: "ACE" },
];

describe("TrumpCallPanel", () => {
  it("shows a waiting message when you're not the bid winner", () => {
    render(
      <TrumpCallPanel isBidWinner={false} isMoonBid={false} yourHand={HAND} onCallTrump={vi.fn()} />,
    );
    expect(screen.getByText(/waiting/i)).toBeInTheDocument();
  });

  it("calls trump immediately on click for a non-moon bid, with no swap card", () => {
    const onCallTrump = vi.fn();
    render(
      <TrumpCallPanel isBidWinner isMoonBid={false} yourHand={HAND} onCallTrump={onCallTrump} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "High" }));
    expect(onCallTrump).toHaveBeenCalledWith("HIGH", null, null);
  });

  it("for a MOON bid, requires both a trump choice and a swap card before confirming", () => {
    const onCallTrump = vi.fn();
    render(<TrumpCallPanel isBidWinner isMoonBid yourHand={HAND} onCallTrump={onCallTrump} />);

    // picking trump alone doesn't call trump yet - it's a MOON bid.
    fireEvent.click(screen.getByRole("button", { name: "High" }));
    expect(onCallTrump).not.toHaveBeenCalled();

    const confirmButton = screen.getByRole("button", { name: /confirm/i });
    expect(confirmButton).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /9 of clubs/i }));
    expect(confirmButton).toBeEnabled();

    fireEvent.click(confirmButton);
    expect(onCallTrump).toHaveBeenCalledWith("HIGH", null, HAND[0]);
  });

  it("lets you switch your swap-card pick to a different card", () => {
    const onCallTrump = vi.fn();
    render(<TrumpCallPanel isBidWinner isMoonBid yourHand={HAND} onCallTrump={onCallTrump} />);
    fireEvent.click(screen.getByRole("button", { name: "High" }));

    const firstCard = screen.getByRole("button", { name: /9 of clubs/i });
    const secondCard = screen.getByRole("button", { name: /a of hearts/i });

    fireEvent.click(firstCard);
    expect(firstCard).toBeEnabled(); // still clickable, not disabled by selecting it
    expect(secondCard).toBeEnabled();

    fireEvent.click(secondCard);
    fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
    expect(onCallTrump).toHaveBeenCalledWith("HIGH", null, HAND[1]);
  });

  it("lets you unselect a swap card by clicking it again, disabling confirm", () => {
    render(<TrumpCallPanel isBidWinner isMoonBid yourHand={HAND} onCallTrump={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "High" }));

    const card = screen.getByRole("button", { name: /9 of clubs/i });
    fireEvent.click(card);
    expect(screen.getByRole("button", { name: /confirm/i })).toBeEnabled();

    fireEvent.click(card);
    expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
  });
});
