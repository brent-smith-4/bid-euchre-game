import { useCallback, useEffect, useRef, useState } from "react";
import type { StateView } from "./protocol";

export type RoundBannerEvent = "bid" | "trick";

export interface RoundBanner {
  winnerId: number | null;
  event: RoundBannerEvent | null;
  dismiss: () => void;
}

// Watches consecutive state broadcasts for two transitions the server
// doesn't announce as discrete events - a bidding round resolving, and a
// trick completing - and surfaces the winner and which of the two happened,
// naming the actual winner rather than framing it from any one viewer's own
// "you won/lost" perspective. Returns structured data rather than a
// pre-built string so the caller can render the winner's name in their
// team's color.
export function useRoundBanner(state: StateView | null): RoundBanner {
  const [winnerId, setWinnerId] = useState<number | null>(null);
  const [event, setEvent] = useState<RoundBannerEvent | null>(null);
  const prevStateRef = useRef<StateView | null>(null);

  useEffect(() => {
    const prev = prevStateRef.current;
    prevStateRef.current = state;
    if (state === null || prev === null) return;

    if (prev.phase === "BIDDING" && state.phase !== "BIDDING" && state.winning_bid) {
      setWinnerId(state.winning_bid.player_id);
      setEvent("bid");
      return;
    }

    if (state.tricks_completed > prev.tricks_completed && state.last_trick_winner !== null) {
      setWinnerId(state.last_trick_winner);
      setEvent("trick");
    }
  }, [state]);

  const dismiss = useCallback(() => {
    setWinnerId(null);
    setEvent(null);
  }, []);

  return { winnerId, event, dismiss };
}
