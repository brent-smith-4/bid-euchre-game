"""Deck construction and dealing. Kept separate from HandState's shape since
shuffling needs an RNG seam for deterministic tests.
"""

from __future__ import annotations

import random

from .models import NUM_PLAYERS, BidRung, Card, Hand, HandState, Rank, Suit, partner_of

CARDS_PER_PLAYER = 6


def build_deck() -> list[Card]:
    """A single 24-card bid euchre deck: 9 through Ace, four suits."""
    return [Card(suit, rank) for suit in Suit for rank in Rank]


def deal_hands(deck: list[Card]) -> dict[int, Hand]:
    """Split a 24-card deck into 6-card hands for players 0-3. Does not
    shuffle — pass an already-shuffled deck.
    """
    expected = NUM_PLAYERS * CARDS_PER_PLAYER
    if len(deck) != expected:
        raise ValueError(f"expected a {expected}-card deck, got {len(deck)}")
    return {
        player_id: deck[player_id * CARDS_PER_PLAYER : (player_id + 1) * CARDS_PER_PLAYER]
        for player_id in range(NUM_PLAYERS)
    }


def deal_new_hand(
    dealer_id: int,
    scores: dict[int, int] | None = None,
    rng: random.Random | None = None,
) -> HandState:
    """Build a fresh, shuffled HandState for the next hand.

    `scores` carries forward the running match score (HandState.scores is
    cumulative across a match, not reset per hand) — pass the previous
    HandState.scores, or omit for the first hand of a match.
    """
    deck = build_deck()
    (rng or random).shuffle(deck)
    hands = deal_hands(deck)
    state = HandState(dealer_id=dealer_id, hands=hands)
    if scores is not None:
        state.scores = dict(scores)
    return state


def swap_moon_card(state: HandState, card_from_bidder: Card, card_from_partner: Card) -> None:
    """Shoot-the-moon card swap: after winning the bid and calling trump, the
    bidder may trade one hidden card with their partner's hand. Requires the
    winning bid to be MOON; raises ValueError otherwise or if either card
    isn't actually held by the player it's claimed from.
    """
    if state.winning_bid is None or state.winning_bid.rung is not BidRung.MOON:
        raise ValueError("card swap is only allowed for a moon bid")

    bidder_id = state.winning_bid.player_id
    partner_id = partner_of(bidder_id)
    bidder_hand = state.hands[bidder_id]
    partner_hand = state.hands[partner_id]

    if card_from_bidder not in bidder_hand:
        raise ValueError("card not in bidder's hand")
    if card_from_partner not in partner_hand:
        raise ValueError("card not in partner's hand")

    bidder_hand.remove(card_from_bidder)
    partner_hand.remove(card_from_partner)
    bidder_hand.append(card_from_partner)
    partner_hand.append(card_from_bidder)
