import { useState } from "react";
import type { Card, Suit, TrumpMode } from "../protocol";
import { cardKey, cardsEqual, suitSymbol } from "../protocol";
import { PlayingCard } from "./PlayingCard";

interface TrumpCallPanelProps {
  isBidWinner: boolean;
  isMoonBid: boolean;
  yourHand: Card[];
  onCallTrump: (mode: TrumpMode, suit: Suit | null, swapOutCard: Card | null) => void;
}

const SUITS: Suit[] = ["CLUBS", "DIAMONDS", "HEARTS", "SPADES"];

// Shown only to the bid winner during CALLING_TRUMP. Winning a MOON bid
// mandatorily bundles the swap-out card into this same call - see
// GameSession.call_trump. Non-MOON bids call trump immediately on click,
// same as before.
export function TrumpCallPanel({ isBidWinner, isMoonBid, yourHand, onCallTrump }: TrumpCallPanelProps) {
  const [pendingTrump, setPendingTrump] = useState<{ mode: TrumpMode; suit: Suit | null } | null>(null);
  const [swapCard, setSwapCard] = useState<Card | null>(null);

  if (!isBidWinner) {
    return <div className="trump-call-panel waiting">Waiting for the bid winner to call trump...</div>;
  }

  const chooseTrump = (mode: TrumpMode, suit: Suit | null) => {
    if (!isMoonBid) {
      onCallTrump(mode, suit, null);
      return;
    }
    setPendingTrump({ mode, suit });
  };

  const confirmMoonCall = () => {
    if (!pendingTrump || !swapCard) return;
    onCallTrump(pendingTrump.mode, pendingTrump.suit, swapCard);
  };

  return (
    <div className="trump-call-panel">
      <p>Call trump:</p>
      <div className="trump-buttons">
        {SUITS.map((suit) => (
          <button
            key={suit}
            type="button"
            className={
              pendingTrump?.mode === "SUIT" && pendingTrump.suit === suit ? "selected" : undefined
            }
            onClick={() => chooseTrump("SUIT", suit)}
          >
            {suitSymbol(suit)}
          </button>
        ))}
        <button
          type="button"
          className={pendingTrump?.mode === "HIGH" ? "selected" : undefined}
          onClick={() => chooseTrump("HIGH", null)}
        >
          High
        </button>
        <button
          type="button"
          className={pendingTrump?.mode === "LOW" ? "selected" : undefined}
          onClick={() => chooseTrump("LOW", null)}
        >
          Low
        </button>
      </div>

      {isMoonBid && (
        <div className="moon-swap-pick">
          <p>
            Shooting the moon: pick one card to swap with your partner (neither of you will know
            what the other picked until after the trade).
          </p>
          <div className="hand">
            {yourHand.map((card) => (
              <PlayingCard
                key={cardKey(card)}
                card={card}
                onClick={() => setSwapCard(swapCard && cardsEqual(swapCard, card) ? null : card)}
                selected={swapCard !== null && cardsEqual(swapCard, card)}
              />
            ))}
          </div>
          <button type="button" disabled={!pendingTrump || !swapCard} onClick={confirmMoonCall}>
            Confirm
          </button>
        </div>
      )}
    </div>
  );
}
