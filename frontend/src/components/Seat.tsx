import type { Card } from "../protocol";
import { playerName } from "../protocol";
import type { TablePosition } from "../seating";
import { CardBack } from "./CardBack";
import { PlayingCard } from "./PlayingCard";

interface SeatProps {
  position: TablePosition;
  playerId: number;
  color: string;
  tricksWon: number;
  isDealer: boolean;
  isTurn: boolean;
  isBot: boolean;
  isYou?: boolean;
  handSize: number;
  // Only passed for the viewer's own seat - renders that many mini cards
  // face up instead of handSize face-down backs. Everyone else's actual
  // cards are never sent to this client in the first place (see
  // build_state_view), so there's no risk of a teammate/opponent's hand
  // ever accidentally rendering face up here.
  yourHand?: Card[];
  names: Record<number, string>;
}

export function Seat({
  position,
  playerId,
  color,
  tricksWon,
  isDealer,
  isTurn,
  isBot,
  isYou,
  handSize,
  yourHand,
  names,
}: SeatProps) {
  return (
    <div className={`seat seat-${position}${isTurn ? " active-turn" : ""}`}>
      <div className="seat-label">
        <span style={{ color }}>{playerName(playerId, names)}</span>
        {isBot && <span className="seat-tag">(Bot)</span>}
        {isYou && <span className="seat-tag">(you)</span>}
        {isDealer && <span className="dealer-marker" title="Dealer">D</span>}
      </div>
      <div className="seat-hand-size">
        {tricksWon} {tricksWon === 1 ? "trick" : "tricks"}
      </div>
      <div className="seat-cards">
        {yourHand
          ? yourHand.map((card) => (
              <PlayingCard key={`${card.suit}-${card.rank}`} card={card} size="mini" />
            ))
          : Array.from({ length: handSize }, (_, i) => <CardBack key={i} size="mini" />)}
      </div>
    </div>
  );
}
