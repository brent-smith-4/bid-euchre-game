import { useEffect, useRef, useState } from "react";
import type { StateView, TrickPlay } from "./protocol";

const HOLD_MS = 2000;

// The server clears current_trick the instant a trick completes (to start
// building the next one) - build_state_view's last_trick field is the only
// place a client ever sees the just-finished trick's 4 cards. Without this
// hook, the table would visually snap empty the moment the 4th card lands,
// at the same time the "you won/lost the trick" banner (useRoundBanner)
// appears. This holds the completed trick on screen for a couple seconds
// before handing back off to whatever the live current_trick is by then.
export function useTrickDisplay(state: StateView | null): TrickPlay[] {
  const [held, setHeld] = useState<TrickPlay[] | null>(null);
  const prevTricksCompletedRef = useRef<number | null>(null);
  // The pending-clear timer lives in a ref, not a useEffect cleanup tied to
  // `state` - a useEffect cleanup would fire on ANY subsequent state update
  // (e.g. the next trick's first card arriving), cancelling the timer
  // without rescheduling it and leaving the trick stuck on screen forever.
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (state === null) return;
    const prev = prevTricksCompletedRef.current;
    prevTricksCompletedRef.current = state.tricks_completed;
    if (prev === null || state.tricks_completed <= prev || !state.last_trick) return;

    if (timerRef.current !== null) clearTimeout(timerRef.current);
    setHeld(state.last_trick);
    timerRef.current = setTimeout(() => {
      setHeld(null);
      timerRef.current = null;
    }, HOLD_MS);
  }, [state]);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, []);

  return held ?? state?.current_trick ?? [];
}
