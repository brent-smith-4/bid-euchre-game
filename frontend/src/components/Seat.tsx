import { playerName } from "../protocol";
import type { TablePosition } from "../seating";

interface SeatProps {
  position: TablePosition;
  playerId: number;
  color: string;
  tricksWon: number;
  isDealer: boolean;
  isTurn: boolean;
  isBot: boolean;
}

export function Seat({ position, playerId, color, tricksWon, isDealer, isTurn, isBot }: SeatProps) {
  return (
    <div className={`seat seat-${position}${isTurn ? " active-turn" : ""}`}>
      <div className="seat-label">
        <span style={{ color }}>{playerName(playerId)}</span>
        {isBot && <span className="bot-marker">(Bot)</span>}
        {isDealer && <span className="dealer-marker" title="Dealer">D</span>}
      </div>
      <div className="seat-hand-size">
        {tricksWon} {tricksWon === 1 ? "trick" : "tricks"}
      </div>
    </div>
  );
}
