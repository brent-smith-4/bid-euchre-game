import { useCallback, useEffect, useRef, useState } from "react";
import type { StateView } from "./protocol";

export interface RoundBanner {
  message: string | null;
  dismiss: () => void;
}

// Watches consecutive state broadcasts for two transitions the server
// doesn't announce as discrete events - a bidding round resolving, and a
// trick completing - and turns each into a one-line "you won/lost the
// bid/trick" notice. Bid outcome is per-player (only one player wins a
// bid); trick outcome is per-team, since the bidder's partner shares the
// trick even though only one seat actually played the winning card.
export function useRoundBanner(state: StateView | null, yourPlayerId: number | null): RoundBanner {
  const [message, setMessage] = useState<string | null>(null);
  const prevStateRef = useRef<StateView | null>(null);

  useEffect(() => {
    const prev = prevStateRef.current;
    prevStateRef.current = state;
    if (state === null || yourPlayerId === null || prev === null) return;

    if (prev.phase === "BIDDING" && state.phase !== "BIDDING" && state.winning_bid) {
      const youWonTheBid = state.winning_bid.player_id === yourPlayerId;
      setMessage(youWonTheBid ? "You won the bid!" : "You lost the bid.");
      return;
    }

    if (state.tricks_completed > prev.tricks_completed && state.last_trick_winner !== null) {
      const yourTeam = yourPlayerId % 2;
      const winningTeam = state.last_trick_winner % 2;
      setMessage(winningTeam === yourTeam ? "Your team won the trick!" : "You lost the trick.");
    }
  }, [state, yourPlayerId]);

  const dismiss = useCallback(() => setMessage(null), []);

  return { message, dismiss };
}
