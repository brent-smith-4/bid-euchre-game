import type { Card } from "../protocol";
import { rankLabel, suitColor, suitSymbol } from "../protocol";

interface PlayingCardProps {
  card: Card;
  // Omit onClick to render a static (already-played) card, e.g. in the
  // trick area - those are never "illegal", so they shouldn't be greyed.
  onClick?: () => void;
  // Only meaningful alongside onClick: greys out a card in the viewer's
  // hand that isn't in this turn's server-provided legal_plays.
  illegal?: boolean;
}

export function PlayingCard({ card, onClick, illegal }: PlayingCardProps) {
  const color = suitColor(card.suit);
  const label = `${rankLabel(card.rank)} of ${card.suit.toLowerCase()}`;

  if (!onClick) {
    return (
      <div className={`playing-card ${color}`} aria-label={label}>
        <span className="rank">{rankLabel(card.rank)}</span>
        <span className="suit">{suitSymbol(card.suit)}</span>
      </div>
    );
  }

  return (
    <button
      type="button"
      className={`playing-card ${color}${illegal ? " illegal" : ""}`}
      onClick={onClick}
      disabled={illegal}
      aria-label={label}
    >
      <span className="rank">{rankLabel(card.rank)}</span>
      <span className="suit">{suitSymbol(card.suit)}</span>
    </button>
  );
}
