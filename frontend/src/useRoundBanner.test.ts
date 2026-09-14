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
    last_trick_winner: null,
    current_trick: [],
    scores: {},
    target_score: 52,
    bidder_turn: null,
    player_turn: null,
    moon_swap_turn: null,
    legal_bids: [],
    legal_plays: [],
    teams: { 0: { color: "#3366cc", name: null }, 1: { color: "#cc3333", name: null } },
    ...overrides,
  };
}

describe("useRoundBanner", () => {
  it("says nothing on the very first state (no prior state to diff against)", () => {
    const { result } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }), yourId: 0 },
    });
    expect(result.current.message).toBeNull();
  });

  it("announces a bid win when bidding resolves in the viewer's favor", () => {
    const { result, rerender } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "BIDDING" }), yourId: 0 },
    });

    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }),
      yourId: 0,
    });
    expect(result.current.message).toBe("You won the bid!");
  });

  it("announces a bid loss when someone else wins the bid", () => {
    const { result, rerender } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "BIDDING" }), yourId: 0 },
    });

    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 2, rung: "THREE" } }),
      yourId: 0,
    });
    expect(result.current.message).toBe("You lost the bid.");
  });

  it("announces a trick win for the viewer's whole team, not just the card-winner", () => {
    const { result, rerender } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "PLAYING", tricks_completed: 0 }), yourId: 0 },
    });

    // player 2 is on the same team as player 0 (team_of = player_id % 2)
    rerender({
      state: makeState({ phase: "PLAYING", tricks_completed: 1, last_trick_winner: 2 }),
      yourId: 0,
    });
    expect(result.current.message).toBe("Your team won the trick!");
  });

  it("announces a trick loss when the other team wins it", () => {
    const { result, rerender } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "PLAYING", tricks_completed: 0 }), yourId: 0 },
    });

    rerender({
      state: makeState({ phase: "PLAYING", tricks_completed: 1, last_trick_winner: 1 }),
      yourId: 0,
    });
    expect(result.current.message).toBe("You lost the trick.");
  });

  it("dismiss clears the message", () => {
    const { result, rerender } = renderHook(({ state, yourId }) => useRoundBanner(state, yourId), {
      initialProps: { state: makeState({ phase: "BIDDING" }), yourId: 0 },
    });
    rerender({
      state: makeState({ phase: "CALLING_TRUMP", winning_bid: { player_id: 0, rung: "THREE" } }),
      yourId: 0,
    });
    expect(result.current.message).not.toBeNull();

    act(() => result.current.dismiss());
    expect(result.current.message).toBeNull();
  });
});
