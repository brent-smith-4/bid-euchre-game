"""Trick logic: which plays are legal, and who wins a completed trick."""

from __future__ import annotations

from .models import NUM_PLAYERS, Bid, BidRung, Card, Hand, Suit, Trick, TrumpCall, partner_of
from .ranking import card_rank_value, effective_suit, is_trump


class IllegalPlayError(ValueError):
    """Raised when an attempted card play is not legal. The message is a
    short machine-readable reason (e.g. "must follow suit") — step 2/3
    decides how to phrase that for players.
    """


def legal_plays(hand: Hand, lead_suit: Suit | None, trump: TrumpCall) -> list[Card]:
    """Cards in `hand` that are legal to play.

    If leading (`lead_suit` is None), any card is legal. Otherwise, must
    follow suit (by effective suit, so the left bower counts as trump) if
    able; if void in the lead suit, any card is legal (trump in or discard).
    """
    if lead_suit is None:
        return list(hand)

    following = [card for card in hand if effective_suit(card, trump) == lead_suit]
    return following if following else list(hand)


def validate_play(card: Card, hand: Hand, lead_suit: Suit | None, trump: TrumpCall) -> None:
    """Raise IllegalPlayError if playing `card` from `hand` isn't legal.

    This is the server-authoritative check step 2 calls before accepting a
    play: the client only ever sees the *result* (legal_plays, for greying
    out cards) but the server re-validates the actual attempt independently.
    """
    if card not in hand:
        raise IllegalPlayError("card not in hand")
    if card not in legal_plays(hand, lead_suit, trump):
        raise IllegalPlayError("must follow suit")


_SOLO_RUNGS = frozenset({BidRung.MOON, BidRung.ALONE})


def active_players(winning_bid: Bid) -> list[int]:
    """Player ids who actually play cards this hand.

    Normally all 4; for MOON or ALONE, the bidder's partner sits out
    entirely (their dealt hand still exists in HandState, it's just never
    played from or included in turn order) - the bidder plays the whole
    hand alone either way. The only difference between the two is the
    pre-play blind card swap (MOON only, see GameSession.call_trump /
    submit_moon_swap_card) and the point value (12 vs 24) - MOON gets one
    assist card from the partner for half of ALONE's payout.
    """
    if winning_bid.rung in _SOLO_RUNGS:
        excluded = partner_of(winning_bid.player_id)
        return [p for p in range(NUM_PLAYERS) if p != excluded]
    return list(range(NUM_PLAYERS))


def trick_play_order(leader_id: int, winning_bid: Bid) -> list[int]:
    """Clockwise play order for one trick starting at `leader_id`, skipping
    the sitting-out partner for MOON/ALONE (so those hands' tricks naturally
    end up with 3 plays instead of 4).
    """
    active = set(active_players(winning_bid))
    clockwise = ((leader_id + offset) % NUM_PLAYERS for offset in range(NUM_PLAYERS))
    return [player_id for player_id in clockwise if player_id in active]


def determine_trick_winner(trick: Trick, trump: TrumpCall) -> int:
    """Return the player_id who won the trick."""
    if not trick:
        raise ValueError("cannot determine a winner for an empty trick")

    lead_suit = effective_suit(trick[0].card, trump)
    contenders = [
        play
        for play in trick
        if effective_suit(play.card, trump) == lead_suit or is_trump(play.card, trump)
    ]
    winner = max(contenders, key=lambda play: card_rank_value(play.card, trump))
    return winner.player_id
