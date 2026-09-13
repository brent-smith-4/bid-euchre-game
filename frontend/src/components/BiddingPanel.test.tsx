import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BiddingPanel } from "./BiddingPanel";

describe("BiddingPanel", () => {
  it("shows a waiting message when it isn't your turn", () => {
    render(<BiddingPanel yourTurn={false} legalBids={[]} onBid={vi.fn()} />);
    expect(screen.getByText(/waiting/i)).toBeInTheDocument();
  });

  it("enables only the rungs the server marked legal, per legal_bids", () => {
    render(<BiddingPanel yourTurn legalBids={["PASS", "FIVE"]} onBid={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Pass" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "5" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "3" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "4" })).toBeDisabled();
  });

  it("sends the chosen rung when a legal bid button is clicked", () => {
    const onBid = vi.fn();
    render(<BiddingPanel yourTurn legalBids={["SIX"]} onBid={onBid} />);

    fireEvent.click(screen.getByRole("button", { name: "6" }));
    expect(onBid).toHaveBeenCalledWith("SIX");
  });
});
