import type { TrickPlay } from "../protocol";
import { cardKey } from "../protocol";
import { relativeSeat } from "../seating";
import { PlayingCard } from "./PlayingCard";

interface TrickAreaProps {
  currentTrick: TrickPlay[];
  yourPlayerId: number;
}

export function TrickArea({ currentTrick, yourPlayerId }: TrickAreaProps) {
  return (
    <div className="trick-area">
      {currentTrick.map((play) => (
        <div key={cardKey(play.card)} className={`trick-play trick-play-${relativeSeat(yourPlayerId, play.player_id)}`}>
          <PlayingCard card={play.card} />
        </div>
      ))}
    </div>
  );
}
