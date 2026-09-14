import type { Card } from "../protocol";
import { rankLabel, suitColor, suitSymbol } from "../protocol";

interface PlayingCardProps {
  card: Card;
  // Omit onClick to render a static (already-played) card, e.g. in the
  // trick area - those are never "illegal", so they shouldn't be greyed.
  onClick?: () => void;
  // Only meaningful alongside onClick: greys out AND disables a card in the
  // viewer's hand that isn't in this turn's server-provided legal_plays -
  // clicking it isn't a valid action at all.
  illegal?: boolean;
  // Only meaningful alongside onClick: highlights a card the player has
  // tentatively picked (e.g. a moon-swap card before confirming) WITHOUT
  // disabling it or any other card - the player must still be able to
  // click a different card to change their pick, or click this one again
  // to unselect it.
  selected?: boolean;
}

export function PlayingCard({ card, onClick, illegal, selected }: PlayingCardProps) {
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
      className={`playing-card ${color}${illegal ? " illegal" : ""}${selected ? " selected" : ""}`}
      onClick={onClick}
      disabled={illegal}
      aria-label={label}
      aria-pressed={selected}
    >
      <span className="rank">{rankLabel(card.rank)}</span>
      <span className="suit">{suitSymbol(card.suit)}</span>
    </button>
  );
}
