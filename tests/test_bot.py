"""Unit tests for the rule-based bot decision logic in bot.py. Pure function
tests - no GameSession/Room involved (that wiring is covered in
test_main.py's bot end-to-end test).
"""

import random

from bid_euchre.models import BidRung, Card, Rank, Suit, TrickPlay, TrumpCall, TrumpMode
from bid_euchre.trick import legal_plays
from bid_euchre_server.bot import choose_bid, choose_card_to_play, choose_moon_swap_card

import pytest

ALL_BIDS = list(BidRung)


def test_weak_hand_never_bids_above_what_it_supports() -> None:
    # Scattered mid/low cards, no bowers, no aces, no anchor-card depth.
    weak_hand = [
        Card(Suit.CLUBS, Rank.TEN),
        Card(Suit.DIAMONDS, Rank.JACK),
        Card(Suit.HEARTS, Rank.QUEEN),
        Card(Suit.SPADES, Rank.KING),
        Card(Suit.CLUBS, Rank.QUEEN),
        Card(Suit.DIAMONDS, Rank.KING),
    ]
    assert choose_bid(weak_hand, ALL_BIDS, is_first_bidder=True) == BidRung.PASS
    assert choose_bid(weak_hand, ALL_BIDS, is_first_bidder=False) == BidRung.PASS

    # Forced (stuck dealer, PASS unavailable): must still not overreach -
    # the cheapest legal rung, not a bid the hand can't support.
    forced_bids = [rung for rung in ALL_BIDS if rung is not BidRung.PASS]
    assert choose_bid(weak_hand, forced_bids, is_first_bidder=True) == BidRung.THREE


def test_bower_and_ace_hand_bids_a_specific_expected_rung() -> None:
    # Right bower + 2 more spades + an off-suit ace: 2.9 suit-mode estimate,
    # rounds to THREE. Not first bidder, so a same-suit-9-driven LOW read
    # (which would otherwise dominate for a first bidder) is capped/moot -
    # this hand only has one 9 anyway, below the not-first anchor threshold.
    hand = [
        Card(Suit.SPADES, Rank.JACK),
        Card(Suit.SPADES, Rank.KING),
        Card(Suit.SPADES, Rank.NINE),
        Card(Suit.HEARTS, Rank.ACE),
        Card(Suit.DIAMONDS, Rank.QUEEN),
        Card(Suit.CLUBS, Rank.TEN),
    ]
    assert choose_bid(hand, ALL_BIDS, is_first_bidder=False) == BidRung.THREE


def test_not_first_bidder_needs_three_anchor_cards_and_is_capped_at_three() -> None:
    # 3 aces plus a matching king: still capped at THREE when not first,
    # regardless of the extra support that would boost a first-bidder's bid.
    three_aces_and_king = [
        Card(Suit.SPADES, Rank.ACE),
        Card(Suit.HEARTS, Rank.ACE),
        Card(Suit.CLUBS, Rank.ACE),
        Card(Suit.SPADES, Rank.KING),
        Card(Suit.DIAMONDS, Rank.NINE),
        Card(Suit.DIAMONDS, Rank.TEN),
    ]
    assert choose_bid(three_aces_and_king, ALL_BIDS, is_first_bidder=False) == BidRung.THREE
    # The same hand, first bidder, is worth more (anchor depth pays off).
    assert choose_bid(three_aces_and_king, ALL_BIDS, is_first_bidder=True) == BidRung.FOUR


def test_dominant_hand_reaches_alone_only_when_first_bidder() -> None:
    # 9,10 of spades + 9,10,Q,K of hearts: every card in an anchored (LOW)
    # suit except the anti-anchor (ace) counts - the entire 6-card hand is
    # "guaranteed" -> ALONE, but only for the first bidder (who can lead to
    # cash it in). Not first, this collapses since no-trump is unviable and
    # the hand falls back to whatever the suit-mode heuristic finds.
    hand = [
        Card(Suit.SPADES, Rank.NINE),
        Card(Suit.SPADES, Rank.TEN),
        Card(Suit.HEARTS, Rank.NINE),
        Card(Suit.HEARTS, Rank.TEN),
        Card(Suit.HEARTS, Rank.QUEEN),
        Card(Suit.HEARTS, Rank.KING),
    ]
    assert choose_bid(hand, ALL_BIDS, is_first_bidder=True) == BidRung.ALONE
    assert choose_bid(hand, ALL_BIDS, is_first_bidder=False) != BidRung.ALONE


def test_choose_card_to_play_never_produces_an_illegal_card() -> None:
    """Fuzz test: many random hands/lead-suit/trump combinations - the
    chosen card must always be a member of the legal_plays given for that
    situation.
    """
    rng = random.Random(1234)
    all_cards = [Card(suit, rank) for suit in Suit for rank in Rank]

    for _ in range(500):
        hand = rng.sample(all_cards, k=rng.randint(1, 6))
        trump = TrumpCall(mode=TrumpMode.SUIT, suit=rng.choice(list(Suit)))

        if rng.random() < 0.5:
            current_trick: list[TrickPlay] = []
            lead_suit = None
        else:
            lead_card = rng.choice(all_cards)
            current_trick = [TrickPlay(player_id=0, card=lead_card)]
            lead_suit = lead_card.suit

        legal = legal_plays(hand, lead_suit, trump)
        choice = choose_card_to_play(hand, legal, current_trick, trump)
        assert choice in legal


def test_choose_card_to_play_wins_with_the_lowest_sufficient_card() -> None:
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)
    current_trick = [TrickPlay(player_id=1, card=Card(Suit.HEARTS, Rank.NINE))]
    hand = [Card(Suit.HEARTS, Rank.KING), Card(Suit.HEARTS, Rank.ACE)]
    legal = hand  # both follow suit

    choice = choose_card_to_play(hand, legal, current_trick, trump)

    assert choice == Card(Suit.HEARTS, Rank.KING)  # wins, and is cheaper than the ace


def test_choose_card_to_play_discards_lowest_when_it_cannot_win() -> None:
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)
    current_trick = [TrickPlay(player_id=1, card=Card(Suit.HEARTS, Rank.ACE))]
    hand = [Card(Suit.HEARTS, Rank.NINE), Card(Suit.HEARTS, Rank.TEN)]
    legal = hand

    choice = choose_card_to_play(hand, legal, current_trick, trump)

    assert choice == Card(Suit.HEARTS, Rank.NINE)


def test_leading_prefers_off_suit_over_trump_even_when_trump_is_the_longest_suit() -> None:
    """Regression: a bidder's partner would otherwise auto-lead trump the
    instant they took the lead, since trump is often their longest/
    strongest suit too. Trump should be held back, not burned leading.
    """
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)
    hand = [
        Card(Suit.SPADES, Rank.ACE),  # 3 trump cards - the "longest suit" trap
        Card(Suit.SPADES, Rank.KING),
        Card(Suit.SPADES, Rank.QUEEN),
        Card(Suit.HEARTS, Rank.NINE),
        Card(Suit.DIAMONDS, Rank.TEN),
    ]
    legal = hand  # leading: anything is legal

    choice = choose_card_to_play(hand, legal, [], trump)

    assert choice == Card(Suit.DIAMONDS, Rank.TEN)  # highest off-suit card, not any spade


def test_leading_plays_lowest_trump_only_once_no_off_suit_cards_remain() -> None:
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)
    hand = [Card(Suit.SPADES, Rank.ACE), Card(Suit.SPADES, Rank.KING), Card(Suit.SPADES, Rank.QUEEN)]
    legal = hand

    choice = choose_card_to_play(hand, legal, [], trump)

    assert choice == Card(Suit.SPADES, Rank.QUEEN)  # lowest of the 3, conserving the rest


def test_choose_moon_swap_card_diverges_by_role() -> None:
    trump = TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)
    hand = [Card(Suit.SPADES, Rank.JACK), Card(Suit.CLUBS, Rank.JACK), Card(Suit.HEARTS, Rank.NINE)]

    bidder_card = choose_moon_swap_card(hand, trump, role="bidder")
    partner_card = choose_moon_swap_card(hand, trump, role="partner")

    assert bidder_card == Card(Suit.HEARTS, Rank.NINE)  # weakest
    assert partner_card == Card(Suit.SPADES, Rank.JACK)  # strongest (right bower)
    assert bidder_card != partner_card
