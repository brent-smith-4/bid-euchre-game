from bid_euchre.models import Card, Rank, Suit, TrumpCall, TrumpMode
from bid_euchre.ranking import card_rank_value, effective_suit, is_trump

import pytest


@pytest.fixture
def spades_trump() -> TrumpCall:
    return TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)


def test_right_bower_beats_left_bower_beats_ace_of_trump(spades_trump: TrumpCall) -> None:
    right_bower = Card(Suit.SPADES, Rank.JACK)
    left_bower = Card(Suit.CLUBS, Rank.JACK)  # same color as spades
    ace_of_trump = Card(Suit.SPADES, Rank.ACE)

    assert card_rank_value(right_bower, spades_trump) > card_rank_value(
        left_bower, spades_trump
    )
    assert card_rank_value(left_bower, spades_trump) > card_rank_value(
        ace_of_trump, spades_trump
    )


def test_off_color_jack_is_not_a_bower(spades_trump: TrumpCall) -> None:
    off_color_jack = Card(Suit.HEARTS, Rank.JACK)  # red, spades trump is black
    ace_of_hearts = Card(Suit.HEARTS, Rank.ACE)
    # a plain off-suit jack ranks by its own printed suit's natural order,
    # below trump entirely
    assert card_rank_value(off_color_jack, spades_trump) < card_rank_value(
        Card(Suit.SPADES, Rank.NINE), spades_trump
    )
    assert card_rank_value(ace_of_hearts, spades_trump) > card_rank_value(
        off_color_jack, spades_trump
    )


def test_trump_suit_outranks_every_non_trump_card(spades_trump: TrumpCall) -> None:
    lowest_trump = Card(Suit.SPADES, Rank.NINE)
    highest_non_trump = Card(Suit.HEARTS, Rank.ACE)
    assert card_rank_value(lowest_trump, spades_trump) > card_rank_value(
        highest_non_trump, spades_trump
    )


def test_left_bower_effective_suit_is_trump_suit(spades_trump: TrumpCall) -> None:
    left_bower = Card(Suit.CLUBS, Rank.JACK)
    assert effective_suit(left_bower, spades_trump) is Suit.SPADES
    assert is_trump(left_bower, spades_trump)


def test_right_bower_effective_suit_is_its_own_suit(spades_trump: TrumpCall) -> None:
    right_bower = Card(Suit.SPADES, Rank.JACK)
    assert effective_suit(right_bower, spades_trump) is Suit.SPADES


def test_no_trump_high_ranks_ace_above_nine() -> None:
    high = TrumpCall(mode=TrumpMode.HIGH)
    ace = Card(Suit.CLUBS, Rank.ACE)
    nine = Card(Suit.CLUBS, Rank.NINE)
    assert card_rank_value(ace, high) > card_rank_value(nine, high)


def test_no_trump_low_ranks_nine_above_ace() -> None:
    low = TrumpCall(mode=TrumpMode.LOW)
    ace = Card(Suit.CLUBS, Rank.ACE)
    nine = Card(Suit.CLUBS, Rank.NINE)
    assert card_rank_value(nine, low) > card_rank_value(ace, low)


def test_no_trump_has_no_bower_logic() -> None:
    high = TrumpCall(mode=TrumpMode.HIGH)
    jack = Card(Suit.CLUBS, Rank.JACK)
    king = Card(Suit.CLUBS, Rank.KING)
    assert card_rank_value(king, high) > card_rank_value(jack, high)
    assert not is_trump(jack, high)


def test_sorting_a_hand_with_builtin_sorted(spades_trump: TrumpCall) -> None:
    hand = [
        Card(Suit.SPADES, Rank.NINE),
        Card(Suit.CLUBS, Rank.JACK),  # left bower
        Card(Suit.SPADES, Rank.JACK),  # right bower
        Card(Suit.HEARTS, Rank.ACE),
    ]
    ranked = sorted(hand, key=lambda c: card_rank_value(c, spades_trump), reverse=True)
    assert ranked == [
        Card(Suit.SPADES, Rank.JACK),
        Card(Suit.CLUBS, Rank.JACK),
        Card(Suit.SPADES, Rank.NINE),
        Card(Suit.HEARTS, Rank.ACE),
    ]
