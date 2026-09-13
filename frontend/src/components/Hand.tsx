import type { Card } from "../protocol";
import { cardKey, cardsEqual } from "../protocol";
import { PlayingCard } from "./PlayingCard";

interface HandProps {
  cards: Card[];
  yourTurn: boolean;
  legalPlays: Card[];
  onPlay: (card: Card) => void;
}

// Display-only sort (suit, then rank) so the hand doesn't reshuffle its
// on-screen order as cards are played - purely cosmetic, not rules logic.
const SUIT_ORDER = ["CLUBS", "DIAMONDS", "HEARTS", "SPADES"];
const RANK_ORDER = ["NINE", "TEN", "JACK", "QUEEN", "KING", "ACE"];

function sortForDisplay(cards: Card[]): Card[] {
  return [...cards].sort((a, b) => {
    const suitDiff = SUIT_ORDER.indexOf(a.suit) - SUIT_ORDER.indexOf(b.suit);
    if (suitDiff !== 0) return suitDiff;
    return RANK_ORDER.indexOf(a.rank) - RANK_ORDER.indexOf(b.rank);
  });
}

export function Hand({ cards, yourTurn, legalPlays, onPlay }: HandProps) {
  const sorted = sortForDisplay(cards);

  return (
    <div className="hand">
      {sorted.map((card) => {
        const isLegal = legalPlays.some((legal) => cardsEqual(legal, card));
        return (
          <PlayingCard
            key={cardKey(card)}
            card={card}
            onClick={yourTurn ? () => onPlay(card) : undefined}
            illegal={yourTurn && !isLegal}
          />
        );
      })}
    </div>
  );
}
