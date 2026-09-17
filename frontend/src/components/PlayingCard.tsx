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
  // "mini" is a small, non-interactive face-up card used for the on-table
  // seat display (see Seat.tsx) - always rendered without onClick.
  size?: "normal" | "mini";
}

function CardFace({ card }: { card: Card }) {
  const rank = rankLabel(card.rank);
  const suit = suitSymbol(card.suit);
  return (
    <>
      <span className="card-index card-index-top">
        <span className="card-index-rank">{rank}</span>
        <span className="card-index-suit">{suit}</span>
      </span>
      <span className="card-pip">{suit}</span>
      <span className="card-index card-index-bottom">
        <span className="card-index-rank">{rank}</span>
        <span className="card-index-suit">{suit}</span>
      </span>
    </>
  );
}

export function PlayingCard({ card, onClick, illegal, selected, size = "normal" }: PlayingCardProps) {
  const color = suitColor(card.suit);
  const label = `${rankLabel(card.rank)} of ${card.suit.toLowerCase()}`;
  const sizeClass = size === "mini" ? " playing-card-mini" : "";

  if (!onClick) {
    return (
      <div className={`playing-card ${color}${sizeClass}`} aria-label={label}>
        <CardFace card={card} />
      </div>
    );
  }

  return (
    <button
      type="button"
      className={`playing-card ${color}${sizeClass}${illegal ? " illegal" : ""}${selected ? " selected" : ""}`}
      onClick={onClick}
      disabled={illegal}
      aria-label={label}
      aria-pressed={selected}
    >
      <CardFace card={card} />
    </button>
  );
}
