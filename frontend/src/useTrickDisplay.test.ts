import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Card, StateView, TrickPlay } from "./protocol";
import { useTrickDisplay } from "./useTrickDisplay";

const CARD_A: Card = { suit: "CLUBS", rank: "NINE" };
const CARD_B: Card = { suit: "HEARTS", rank: "TEN" };

function makeState(overrides: Partial<StateView>): StateView {
  return {
    type: "state",
    phase: "PLAYING",
    your_player_id: 0,
    dealer_id: 0,
    your_hand: [],
    hand_sizes: {},
    bid_history: [],
    winning_bid: null,
    trump: null,
    tricks_completed: 0,
    tricks_won: {},
    last_trick_winner: null,
    last_trick: null,
    current_trick: [],
    scores: {},
    target_score: 52,
    bidder_turn: null,
    player_turn: null,
    moon_swap_turn: null,
    legal_bids: [],
    legal_plays: [],
    teams: { 0: { color: "#3366cc", name: null }, 1: { color: "#cc3333", name: null } },
    bots: [],
    is_host: false,
    ...overrides,
  };
}

describe("useTrickDisplay", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows the live current_trick when no trick has just completed", () => {
    const currentTrick: TrickPlay[] = [{ player_id: 1, card: CARD_A }];
    const { result } = renderHook(({ state }) => useTrickDisplay(state), {
      initialProps: { state: makeState({ current_trick: currentTrick }) },
    });
    expect(result.current).toBe(currentTrick);
  });

  it("holds the completed trick on screen even as a new trick starts building, then hands off", () => {
    const finishedTrick: TrickPlay[] = [
      { player_id: 0, card: CARD_A },
      { player_id: 1, card: CARD_B },
    ];
    const { result, rerender } = renderHook(({ state }) => useTrickDisplay(state), {
      initialProps: { state: makeState({ tricks_completed: 0, current_trick: [] }) },
    });

    // the trick completes: tricks_completed increments, last_trick is set,
    // and current_trick has already been cleared by the server.
    rerender({
      state: makeState({ tricks_completed: 1, last_trick: finishedTrick, current_trick: [] }),
    });
    expect(result.current).toBe(finishedTrick);

    // the next trick starts building for real - still held, not the new card.
    const newCard: TrickPlay[] = [{ player_id: 2, card: CARD_A }];
    rerender({
      state: makeState({ tricks_completed: 1, last_trick: finishedTrick, current_trick: newCard }),
    });
    expect(result.current).toBe(finishedTrick);

    // after the hold window, hands off to whatever current_trick is by then.
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current).toBe(newCard);
  });

  it("replaces the held trick immediately if a second trick completes before the hold expires", () => {
    const firstTrick: TrickPlay[] = [{ player_id: 0, card: CARD_A }];
    const secondTrick: TrickPlay[] = [{ player_id: 1, card: CARD_B }];
    const { result, rerender } = renderHook(({ state }) => useTrickDisplay(state), {
      initialProps: { state: makeState({ tricks_completed: 0 }) },
    });

    rerender({ state: makeState({ tricks_completed: 1, last_trick: firstTrick }) });
    expect(result.current).toBe(firstTrick);

    act(() => vi.advanceTimersByTime(500));
    rerender({ state: makeState({ tricks_completed: 2, last_trick: secondTrick }) });
    expect(result.current).toBe(secondTrick);
  });
});
