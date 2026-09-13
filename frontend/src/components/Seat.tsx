import { playerName } from "../protocol";
import type { TablePosition } from "../seating";

interface SeatProps {
  position: TablePosition;
  playerId: number;
  handSize: number;
  isDealer: boolean;
  isTurn: boolean;
}

export function Seat({ position, playerId, handSize, isDealer, isTurn }: SeatProps) {
  return (
    <div className={`seat seat-${position}${isTurn ? " active-turn" : ""}`}>
      <div className="seat-label">
        {playerName(playerId)}
        {isDealer && <span className="dealer-marker" title="Dealer">D</span>}
      </div>
      <div className="seat-hand-size">{handSize} cards</div>
    </div>
  );
}
