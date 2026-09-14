import { useState } from "react";
import type { Card } from "../protocol";
import { cardKey, cardsEqual } from "../protocol";
import { PlayingCard } from "./PlayingCard";

interface MoonSwapPanelProps {
  isYourTurn: boolean;
  isBidder: boolean;
  yourHand: Card[];
  onSubmitSwapCard: (card: Card) => void;
}

// Shown during Phase.MOON_SWAP, after the bidder has already named their
// outgoing card (server-side only - never sent to any client). Only the
// bidder's partner acts here; everyone else just waits. Fully blind: this
// panel never learns which card the bidder is giving.
export function MoonSwapPanel({ isYourTurn, isBidder, yourHand, onSubmitSwapCard }: MoonSwapPanelProps) {
  const [chosenCard, setChosenCard] = useState<Card | null>(null);

  if (!isYourTurn) {
    return (
      <div className="moon-swap-panel waiting">
        {isBidder
          ? "Waiting for your partner to choose a card to send you..."
          : "Waiting for the shoot-the-moon card swap..."}
      </div>
    );
  }

  return (
    <div className="moon-swap-panel">
      <p>
        Your partner is shooting the moon and has picked a card to give you (you won't know which
        until the trade happens). Pick one of your own cards to send back:
      </p>
      <div className="hand">
        {yourHand.map((card) => (
          <PlayingCard
            key={cardKey(card)}
            card={card}
            onClick={() => setChosenCard(chosenCard && cardsEqual(chosenCard, card) ? null : card)}
            selected={chosenCard !== null && cardsEqual(chosenCard, card)}
          />
        ))}
      </div>
      <button
        type="button"
        disabled={!chosenCard}
        onClick={() => chosenCard && onSubmitSwapCard(chosenCard)}
      >
        Confirm
      </button>
    </div>
  );
}
