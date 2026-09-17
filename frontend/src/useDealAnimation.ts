import { useEffect, useRef, useState } from "react";
import type { StateView } from "./protocol";
import type { TablePosition } from "./seating";
import { relativeSeat } from "./seating";

export interface DealCardSprite {
  id: string;
  position: TablePosition;
  delayMs: number;
}

export interface DealAnimation {
  sprites: DealCardSprite[];
  // player_id -> how many of their cards have "landed" so far - Table/Seat
  // use this to reveal a player's on-table cards 2 at a time in step with
  // the animation, instead of the real (already fully dealt) hand showing
  // all 6 the instant the hand arrives.
  revealedCounts: Record<number, number>;
}

const CARDS_PER_ROUND = 2;
const ROUNDS = 3; // 6 cards per player, dealt 2 at a time
const TOTAL_STEPS = ROUNDS * 4;
const STEP_MS = 150; // time between each player's turn to receive a round
const CARD_STAGGER_MS = 60; // the 2 cards within one player's turn land slightly apart
const ANIMATION_MS = 450; // must match .deal-card's animation-duration in App.css
const CLEAR_BUFFER_MS = 300;

function stepSeatId(dealerId: number, stepIndex: number): number {
  const leftOfDealer = (dealerId + 1) % 4;
  return (leftOfDealer + (stepIndex % 4)) % 4;
}

function buildDealSequence(dealerId: number, yourPlayerId: number): DealCardSprite[] {
  const sprites: DealCardSprite[] = [];
  for (let stepIndex = 0; stepIndex < TOTAL_STEPS; stepIndex++) {
    const seatId = stepSeatId(dealerId, stepIndex);
    const position = relativeSeat(yourPlayerId, seatId);
    for (let c = 0; c < CARDS_PER_ROUND; c++) {
      sprites.push({
        id: `${stepIndex}-${c}`,
        position,
        delayMs: stepIndex * STEP_MS + c * CARD_STAGGER_MS,
      });
    }
  }
  return sprites;
}

// Plays a one-time "shuffle and deal" overlay animation (see Table.tsx/
// App.css's .deal-card) whenever a fresh hand starts - purely decorative,
// layered on top of the table. Every hand's dealer_id strictly increments
// (mod 4) - deal_new_hand always advances it by exactly 1 - so a dealer_id
// different from the last one we saw, combined with a hand that has no bids
// or tricks yet, uniquely identifies "a fresh hand was just dealt" without
// the server needing to announce it as its own discrete event.
export function useDealAnimation(state: StateView | null, yourPlayerId: number | null): DealAnimation | null {
  const [animation, setAnimation] = useState<DealAnimation | null>(null);
  // -1 is not a real dealer_id, so the very first state this hook ever
  // sees - including the first hand of a brand-new match - still counts as
  // "different from the last dealer we saw" and gets animated too.
  const prevDealerRef = useRef<number>(-1);
  // Timers live in a ref, not a useEffect cleanup tied to `state` - see
  // useTrickDisplay's identical reasoning: a cleanup tied to the dependency
  // would fire (and cancel every pending timer) on every subsequent
  // broadcast during bidding, not just the one that started this animation.
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (state === null || yourPlayerId === null) return;
    const prevDealerId = prevDealerRef.current;
    prevDealerRef.current = state.dealer_id;

    const isFreshDeal =
      prevDealerId !== state.dealer_id && state.bid_history.length === 0 && state.tricks_completed === 0;
    if (!isFreshDeal) return;

    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    const dealerId = state.dealer_id;
    const sprites = buildDealSequence(dealerId, yourPlayerId);
    setAnimation({ sprites, revealedCounts: { 0: 0, 1: 0, 2: 0, 3: 0 } });

    for (let stepIndex = 0; stepIndex < TOTAL_STEPS; stepIndex++) {
      const seatId = stepSeatId(dealerId, stepIndex);
      const cardsSoFar = (Math.floor(stepIndex / 4) + 1) * CARDS_PER_ROUND;
      const revealTime = stepIndex * STEP_MS + ANIMATION_MS;
      timersRef.current.push(
        setTimeout(() => {
          setAnimation((prev) =>
            prev ? { ...prev, revealedCounts: { ...prev.revealedCounts, [seatId]: cardsSoFar } } : prev,
          );
        }, revealTime),
      );
    }

    const lastDelay = (TOTAL_STEPS - 1) * STEP_MS + (CARDS_PER_ROUND - 1) * CARD_STAGGER_MS;
    timersRef.current.push(
      setTimeout(() => {
        setAnimation(null);
      }, lastDelay + ANIMATION_MS + CLEAR_BUFFER_MS),
    );
  }, [state, yourPlayerId]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach(clearTimeout);
    };
  }, []);

  return animation;
}
