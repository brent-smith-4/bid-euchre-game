import type { TrickPlay } from "../protocol";
import { cardKey } from "../protocol";
import type { TablePosition } from "../seating";
import { relativeSeat } from "../seating";
import { CardBack } from "./CardBack";
import { PlayingCard } from "./PlayingCard";

interface TrickAreaProps {
  currentTrick: TrickPlay[];
  // Set only while currentTrick is a just-completed trick being held on
  // screen (see useTrickDisplay) - triggers each card to flip face down and
  // fly toward the winner's seat, timed to finish right as the hold ends.
  winnerPosition: TablePosition | null;
  yourPlayerId: number;
}

export function TrickArea({ currentTrick, winnerPosition, yourPlayerId }: TrickAreaProps) {
  return (
    <div className="trick-area">
      {currentTrick.map((play) => (
        <div
          key={cardKey(play.card)}
          className={`trick-play trick-play-${relativeSeat(yourPlayerId, play.player_id)}`}
        >
          <div className={`trick-card-flip${winnerPosition ? ` sweeping fly-to-${winnerPosition}` : ""}`}>
            <div className="trick-card-front">
              <PlayingCard card={play.card} />
            </div>
            <div className="trick-card-back">
              <CardBack />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
