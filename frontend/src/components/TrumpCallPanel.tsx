import type { Suit, TrumpMode } from "../protocol";
import { suitSymbol } from "../protocol";

interface TrumpCallPanelProps {
  isBidWinner: boolean;
  onCallTrump: (mode: TrumpMode, suit: Suit | null) => void;
}

const SUITS: Suit[] = ["CLUBS", "DIAMONDS", "HEARTS", "SPADES"];

// Shown only to the bid winner during CALLING_TRUMP. The moon/alone card
// swap (winning a MOON bid lets the bidder trade one hidden card with their
// partner) is intentionally not offered here yet - see the deferred
// moon-swap-protocol-gap memory note. MOON/ALONE bids still play normally.
export function TrumpCallPanel({ isBidWinner, onCallTrump }: TrumpCallPanelProps) {
  if (!isBidWinner) {
    return <div className="trump-call-panel waiting">Waiting for the bid winner to call trump...</div>;
  }

  return (
    <div className="trump-call-panel">
      <p>Call trump:</p>
      <div className="trump-buttons">
        {SUITS.map((suit) => (
          <button key={suit} type="button" onClick={() => onCallTrump("SUIT", suit)}>
            {suitSymbol(suit)}
          </button>
        ))}
        <button type="button" onClick={() => onCallTrump("HIGH", null)}>
          High
        </button>
        <button type="button" onClick={() => onCallTrump("LOW", null)}>
          Low
        </button>
      </div>
    </div>
  );
}
