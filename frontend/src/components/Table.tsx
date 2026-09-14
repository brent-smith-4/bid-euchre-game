import type { StateView, TrickPlay } from "../protocol";
import { playerColor } from "../protocol";
import { relativeSeat } from "../seating";
import { Seat } from "./Seat";
import { TrickArea } from "./TrickArea";

interface TableProps {
  state: StateView;
  yourPlayerId: number;
  // Defaults to state.current_trick if omitted - callers pass the
  // useTrickDisplay hook's result to briefly hold a just-completed trick on
  // screen instead of it vanishing the instant the 4th card lands.
  displayedTrick?: TrickPlay[];
}

export function Table({ state, yourPlayerId, displayedTrick }: TableProps) {
  const opponents = [0, 1, 2, 3].filter((id) => id !== yourPlayerId);

  return (
    <div className="table">
      {opponents.map((playerId) => (
        <Seat
          key={playerId}
          position={relativeSeat(yourPlayerId, playerId)}
          playerId={playerId}
          color={playerColor(state.teams, playerId)}
          tricksWon={state.tricks_won[playerId] ?? 0}
          isDealer={state.dealer_id === playerId}
          isTurn={state.bidder_turn === playerId || state.player_turn === playerId}
          isBot={state.bots.includes(playerId)}
        />
      ))}
      <TrickArea currentTrick={displayedTrick ?? state.current_trick} yourPlayerId={yourPlayerId} />
    </div>
  );
}
