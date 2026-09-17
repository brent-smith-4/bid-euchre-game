import type { CSSProperties } from "react";
import type { StateView } from "../protocol";
import { playerColor } from "../protocol";
import { relativeSeat } from "../seating";
import type { DealAnimation } from "../useDealAnimation";
import type { TrickDisplay } from "../useTrickDisplay";
import { CardBack } from "./CardBack";
import { Seat } from "./Seat";
import { TrickArea } from "./TrickArea";

interface TableProps {
  state: StateView;
  yourPlayerId: number;
  trickDisplay: TrickDisplay;
  // Lifted up to GameRoom (rather than called here) so the below-table
  // interactive Hand can reveal in step with the on-table seat fans too -
  // see GameRoom.tsx.
  deal: DealAnimation | null;
}

export function Table({ state, yourPlayerId, trickDisplay, deal }: TableProps) {
  return (
    <div className="table">
      {[0, 1, 2, 3].map((playerId) => {
        const realHandSize = state.hand_sizes[playerId] ?? 0;
        const revealed = deal ? Math.min(deal.revealedCounts[playerId] ?? 0, realHandSize) : realHandSize;
        const yourHand = playerId === yourPlayerId ? state.your_hand.slice(0, revealed) : undefined;
        return (
          <Seat
            key={playerId}
            position={relativeSeat(yourPlayerId, playerId)}
            playerId={playerId}
            color={playerColor(state.teams, playerId)}
            tricksWon={state.tricks_won[playerId] ?? 0}
            isDealer={state.dealer_id === playerId}
            isTurn={state.bidder_turn === playerId || state.player_turn === playerId}
            isBot={state.bots.includes(playerId)}
            isYou={playerId === yourPlayerId}
            handSize={revealed}
            yourHand={yourHand}
            names={state.player_names}
          />
        );
      })}
      <TrickArea
        currentTrick={trickDisplay.cards}
        winnerPosition={trickDisplay.winnerId !== null ? relativeSeat(yourPlayerId, trickDisplay.winnerId) : null}
        yourPlayerId={yourPlayerId}
      />
      {deal && (
        <div className="deal-overlay">
          {deal.sprites.map((sprite) => (
            <div
              key={sprite.id}
              className={`deal-card fly-to-${sprite.position}`}
              style={{ "--fly-delay": `${sprite.delayMs}ms` } as CSSProperties}
            >
              <CardBack size="mini" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
