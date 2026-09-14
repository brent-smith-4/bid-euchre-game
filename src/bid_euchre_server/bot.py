"""Rule-based bot decision logic - no training data, no learned models, no RL.

A bot is just another player_id taking its turn through the exact same
GameSession methods a human's WebSocket message handler calls (see
resolve_bot_turns in main.py). This module only computes WHAT a bot decides;
it never touches GameSession or network state directly, and nothing in
bid_euchre (the rules engine) imports or knows about this module - bots are
entirely a bid_euchre_server-layer concept.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from bid_euchre.models import BidRung, Card, Hand, Rank, Suit, Trick, TrickPlay, TrumpCall, TrumpMode
from bid_euchre.ranking import card_rank_value, is_left_bower, is_right_bower, is_trump
from bid_euchre.trick import determine_trick_winner

# Placeholder id for simulating "what if I played this card" in
# choose_card_to_play - never a real seat (those are always 0-3), so a
# hypothetical trick's winner equaling this tells us our candidate won.
_SIMULATED_PLAYER_ID = -1

# -- suit/bower-based estimate (unchanged regardless of bid position) -------
#
# Tuned by feel, not fit to data - these are rough weights for "how many
# tricks can I likely win with this suit as trump," not a probability model.
_OTHER_TRUMP_BASE = 0.4
_OTHER_TRUMP_PER_RANK = 0.15
_OFF_SUIT_ACE_VALUE = 0.5

# Both bowers plus this many total trump cards AND a trick estimate this
# high unlocks the given rare bid. Bower presence + card count alone isn't
# enough - a hand can have both bowers and still only be worth ~4 tricks
# overall, nowhere near enough to justify committing to all 6; the estimate
# itself also has to be close to a full sweep before bidding one.
_SUIT_MOON_MIN_TRUMP_CARDS = 3
_SUIT_MOON_MIN_TRICKS = 5.0
_SUIT_ALONE_MIN_TRUMP_CARDS = 4
_SUIT_ALONE_MIN_TRICKS = 5.5

# -- no-trump (HIGH/LOW) estimate: depends on bidding position --------------
#
# No-trump has no bowers/trump to fall back on: if you're void in the suit
# led, you simply can't win that trick, full stop. The only reliable way to
# win a trick at all is holding the single best card for that suit under
# this mode's ordering (the "anchor" - ACE for HIGH, NINE for LOW), which
# also lets you regain the lead and cash in on other cards. Suit doesn't
# matter for WHICH suits your anchors are in - only how many anchors you
# hold - UNLESS you're the one who gets to lead:
#
# The player left of the dealer bids first AND leads the first trick if they
# win the bid (see CLAUDE.md / GameSession._begin_trick_play). Only that
# seat can guarantee WHEN a specific suit gets played by leading it
# themselves, so only for them does holding OTHER cards in an anchored suit
# actually pay off (lead the anchor to win and regain the lead, then lead
# the next-best card in that same suit, and so on). Anyone else has no such
# control, so their no-trump call needs a much blunter, suit-independent
# signal to be worth the risk at all: holding most of the single best card
# across suits, and even then only ever a minimum bid.
_TOP_RANK_FOR_MODE = {TrumpMode.HIGH: Rank.ACE, TrumpMode.LOW: Rank.NINE}
_ANTI_ANCHOR_RANK_FOR_MODE = {TrumpMode.HIGH: Rank.NINE, TrumpMode.LOW: Rank.ACE}
_NOT_FIRST_MIN_ANCHOR_CARDS = 3
_NOT_FIRST_BID_VALUE = 3

_NO_TRUMP_MOON_MIN_TRICKS = 5
_NO_TRUMP_ALONE_MIN_TRICKS = 6


@dataclass(frozen=True)
class _BidOption:
    """One candidate trump/no-trump call and what it's worth, on a common
    comparable integer "tricks" scale so suit and no-trump options can be
    ranked against each other directly.
    """

    trump: TrumpCall
    tricks: int
    unlocks_moon: bool
    unlocks_alone: bool


def _suit_option(hand: Hand, suit: Suit) -> _BidOption:
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=suit)
    tricks = 0.0
    trump_card_count = 0
    has_right = has_left = False

    for card in hand:
        if is_right_bower(card, suit):
            tricks += 1.0
            trump_card_count += 1
            has_right = True
        elif is_left_bower(card, suit):
            tricks += 1.0
            trump_card_count += 1
            has_left = True
        elif card.suit is suit:
            trump_card_count += 1
            tricks += _OTHER_TRUMP_BASE + _OTHER_TRUMP_PER_RANK * card.rank.value
        elif card.rank is Rank.ACE:
            tricks += _OFF_SUIT_ACE_VALUE

    has_both_bowers = has_right and has_left
    unlocks_alone = (
        has_both_bowers and trump_card_count >= _SUIT_ALONE_MIN_TRUMP_CARDS and tricks >= _SUIT_ALONE_MIN_TRICKS
    )
    unlocks_moon = (
        has_both_bowers and trump_card_count >= _SUIT_MOON_MIN_TRUMP_CARDS and tricks >= _SUIT_MOON_MIN_TRICKS
    )
    return _BidOption(
        trump=trump,
        tricks=math.floor(tricks + 0.5),  # round-half-up onto the shared integer scale
        unlocks_moon=unlocks_moon,
        unlocks_alone=unlocks_alone,
    )


def _anchored_suit_card_count(hand: Hand, suit: Suit, mode: TrumpMode) -> int:
    """Cards held in `suit`, counted only if the anchor of that suit is also
    held (without it, nothing else you hold in that suit is safe from
    whoever else has it) - excluding the anti-anchor (the single WORST card
    under `mode`, e.g. a plain NINE under HIGH), which can never win a trick
    no matter what else you hold alongside it. Every other card counts, gaps
    in rank included (holding 9/10/Q/K of a suit under LOW but not the J
    still credits all 4, not just the unbroken 9-10 prefix) - once the
    anchor has dealt with the one real threat, the rest just get cashed in
    as the suit gets led again.
    """
    anchor = _TOP_RANK_FOR_MODE[mode]
    anti_anchor = _ANTI_ANCHOR_RANK_FOR_MODE[mode]
    held = [card for card in hand if card.suit is suit]
    if not any(card.rank is anchor for card in held):
        return 0
    return sum(1 for card in held if card.rank is not anti_anchor)


def _no_trump_option(hand: Hand, mode: TrumpMode, is_first_bidder: bool) -> _BidOption:
    if is_first_bidder:
        tricks = sum(_anchored_suit_card_count(hand, suit, mode) for suit in Suit)
    else:
        anchor = _TOP_RANK_FOR_MODE[mode]
        anchor_count = sum(1 for card in hand if card.rank is anchor)
        tricks = _NOT_FIRST_BID_VALUE if anchor_count >= _NOT_FIRST_MIN_ANCHOR_CARDS else 0

    return _BidOption(
        trump=TrumpCall(mode=mode),
        tricks=tricks,
        unlocks_moon=is_first_bidder and tricks >= _NO_TRUMP_MOON_MIN_TRICKS,
        unlocks_alone=is_first_bidder and tricks >= _NO_TRUMP_ALONE_MIN_TRICKS,
    )


def best_bid_option(hand: Hand, is_first_bidder: bool) -> _BidOption:
    """The strongest call available - a suit, or no-trump HIGH/LOW - on the
    shared integer tricks scale. Ties favor a trump suit over no-trump,
    since bowers give more control than raw high cards.
    """
    options = [_suit_option(hand, suit) for suit in Suit]
    options.append(_no_trump_option(hand, TrumpMode.HIGH, is_first_bidder))
    options.append(_no_trump_option(hand, TrumpMode.LOW, is_first_bidder))
    return max(options, key=lambda option: option.tricks)


def choose_trump(hand: Hand, is_first_bidder: bool) -> TrumpCall:
    """Which trump/no-trump to call after winning the bid - reuses the exact
    same scoring `choose_bid` used to decide the bid amount, since neither
    the hand nor the bidding position has changed in the meantime.
    """
    return best_bid_option(hand, is_first_bidder).trump


def choose_bid(hand: Hand, legal_bids: list[BidRung], is_first_bidder: bool) -> BidRung:
    """Bid near the hand's estimated trick-taking strength, never just the
    ladder max because it happens to be legal. `is_first_bidder` is whether
    this seat is left-of-dealer (see module docstring above) - it changes
    how a no-trump call is scored, not how a trump-suit call is scored.
    """
    best = best_bid_option(hand, is_first_bidder)

    if best.unlocks_alone and BidRung.ALONE in legal_bids:
        return BidRung.ALONE
    if best.unlocks_moon and BidRung.MOON in legal_bids:
        return BidRung.MOON

    number_bids = (BidRung.THREE, BidRung.FOUR, BidRung.FIVE, BidRung.SIX)
    affordable = [rung for rung in legal_bids if rung in number_bids and rung.value <= best.tricks]
    if affordable:
        return max(affordable, key=lambda rung: rung.value)

    if BidRung.PASS in legal_bids:
        return BidRung.PASS

    # Forced (stuck dealer) and the hand doesn't support even THREE - bid the
    # cheapest legal rung rather than inventing a bid the hand can't back up.
    return min(legal_bids, key=lambda rung: rung.value)


def choose_moon_swap_card(hand: Hand, trump: TrumpCall, *, role: Literal["bidder", "partner"]) -> Card:
    """Which card to give away in the mandatory MOON swap (see
    GameSession.call_trump/submit_moon_swap_card) - trump is already known
    at this point, so this is trump-aware via the same `card_rank_value`
    `determine_trick_winner` itself uses, not a naive rank-only comparison.

    As the bidder, gives away the WEAKEST card - the bidder keeps strength
    for their own hand, since they're the one steering the hand. As the
    partner, gives away the STRONGEST card - the whole point of the swap is
    helping the bidder make all 6 tricks, so the partner sacrifices its
    best rather than a throwaway.
    """
    ranked = sorted(hand, key=lambda card: card_rank_value(card, trump))
    return ranked[0] if role == "bidder" else ranked[-1]


def choose_card_to_play(hand: Hand, legal_plays: list[Card], current_trick: Trick, trump: TrumpCall) -> Card:
    """Never reimplements follow-suit - `legal_plays` (from
    GameSession.legal_plays, itself built on bid_euchre.trick.legal_plays)
    is the only candidate pool considered.
    """
    if not current_trick:
        # Leading: prefer off-suit cards over trump - trump is precious and
        # should be held back for when it's actually needed to win a trick,
        # not burned leading with it. Without this, a bidder's PARTNER would
        # auto-lead trump the instant they took the lead, since trump is
        # often their longest/strongest suit too (a real bug: trump has no
        # bower-style concept in HIGH/LOW no-trump, so `is_trump` is simply
        # always False there and this reduces to "lead the strongest legal
        # card," unaffected). Lead the highest off-suit card available; only
        # lead trump - the lowest one held, conserving the rest - once no
        # off-suit cards remain.
        off_suit = [card for card in legal_plays if not is_trump(card, trump)]
        if off_suit:
            return max(off_suit, key=lambda card: card_rank_value(card, trump))
        return min(legal_plays, key=lambda card: card_rank_value(card, trump))

    # Not leading: reuse determine_trick_winner to check, for each candidate,
    # whether playing it would currently win the trick (simulating
    # current_trick + that play) rather than re-deriving trick-winner logic.
    winning_candidates = []
    for card in legal_plays:
        hypothetical_trick = [*current_trick, TrickPlay(player_id=_SIMULATED_PLAYER_ID, card=card)]
        if determine_trick_winner(hypothetical_trick, trump) == _SIMULATED_PLAYER_ID:
            winning_candidates.append(card)

    if winning_candidates:
        # Win efficiently: the lowest card that still wins, never wasting a
        # bower/ace when a lesser card in hand also wins.
        return min(winning_candidates, key=lambda card: card_rank_value(card, trump))

    # Can't win this trick: discard the weakest legal card.
    return min(legal_plays, key=lambda card: card_rank_value(card, trump))
