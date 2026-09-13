import type { StateView } from "../protocol";
import { relativeSeat } from "../seating";
import { Seat } from "./Seat";
import { TrickArea } from "./TrickArea";

interface TableProps {
  state: StateView;
  yourPlayerId: number;
}

export function Table({ state, yourPlayerId }: TableProps) {
  const opponents = [0, 1, 2, 3].filter((id) => id !== yourPlayerId);

  return (
    <div className="table">
      {opponents.map((playerId) => (
        <Seat
          key={playerId}
          position={relativeSeat(yourPlayerId, playerId)}
          playerId={playerId}
          handSize={state.hand_sizes[playerId] ?? 0}
          isDealer={state.dealer_id === playerId}
          isTurn={state.bidder_turn === playerId || state.player_turn === playerId}
        />
      ))}
      <TrickArea currentTrick={state.current_trick} yourPlayerId={yourPlayerId} />
    </div>
  );
}
