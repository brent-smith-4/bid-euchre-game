import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { StateView } from "./protocol";
import { useRoundBanner } from "./useRoundBanner";

function makeState(overrides: Partial<StateView>): StateView {
  return {
    type: "state",
    phase: "BIDDING",
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
    player_names: {},
    ...overrides,
  };
}

describe("useRoundBanner", () => {
  it("says nothing on the very first state (no prior state to diff against)", () => {
    const { result } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }) },
    });
    expect(result.current.winnerId).toBeNull();
    expect(result.current.event).toBeNull();
  });

  it("announces who won the bid", () => {
    const { result, rerender } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "BIDDING" }) },
    });

    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }),
    });
    expect(result.current.winnerId).toBe(0);
    expect(result.current.event).toBe("bid");
  });

  it("announces a different bid winner by id", () => {
    const { result, rerender } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "BIDDING" }) },
    });

    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 2, rung: "THREE" } }),
    });
    expect(result.current.winnerId).toBe(2);
    expect(result.current.event).toBe("bid");
  });

  it("announces who won the trick", () => {
    const { result, rerender } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "PLAYING", tricks_completed: 0 }) },
    });

    rerender({
      state: makeState({ phase: "PLAYING", tricks_completed: 1, last_trick_winner: 2 }),
    });
    expect(result.current.winnerId).toBe(2);
    expect(result.current.event).toBe("trick");
  });

  it("announces a different trick winner by id", () => {
    const { result, rerender } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "PLAYING", tricks_completed: 0 }) },
    });

    rerender({
      state: makeState({ phase: "PLAYING", tricks_completed: 1, last_trick_winner: 1 }),
    });
    expect(result.current.winnerId).toBe(1);
    expect(result.current.event).toBe("trick");
  });

  it("dismiss clears the winner and event", () => {
    const { result, rerender } = renderHook(({ state }) => useRoundBanner(state), {
      initialProps: { state: makeState({ phase: "BIDDING" }) },
    });
    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }),
    });
    expect(result.current.winnerId).not.toBeNull();

    act(() => result.current.dismiss());
    expect(result.current.winnerId).toBeNull();
    expect(result.current.event).toBeNull();
  });
});
