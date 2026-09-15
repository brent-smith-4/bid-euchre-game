from bid_euchre.models import Bid, BidRung, Card, Rank, Suit, TrickPlay, TrumpCall, TrumpMode
from bid_euchre.trick import (
    IllegalPlayError,
    active_players,
    determine_trick_winner,
    legal_plays,
    trick_play_order,
    validate_play,
)

import pytest


@pytest.fixture
def spades_trump() -> TrumpCall:
    return TrumpCall(mode=TrumpMode.SUIT, suit=Suit.SPADES)


def test_leading_any_card_is_legal(spades_trump: TrumpCall) -> None:
    hand = [Card(Suit.CLUBS, Rank.NINE), Card(Suit.HEARTS, Rank.ACE)]
    assert legal_plays(hand, lead_suit=None, trump=spades_trump) == hand


def test_must_follow_suit_if_able(spades_trump: TrumpCall) -> None:
    hand = [
        Card(Suit.HEARTS, Rank.NINE),
        Card(Suit.HEARTS, Rank.KING),
        Card(Suit.CLUBS, Rank.ACE),
    ]
    legal = legal_plays(hand, lead_suit=Suit.HEARTS, trump=spades_trump)
    assert legal == [Card(Suit.HEARTS, Rank.NINE), Card(Suit.HEARTS, Rank.KING)]


def test_left_bower_counts_as_trump_for_follow_suit(spades_trump: TrumpCall) -> None:
    left_bower = Card(Suit.CLUBS, Rank.JACK)
    hand = [left_bower, Card(Suit.CLUBS, Rank.NINE)]
    # lead suit is spades (trump); left bower (printed clubs) must follow
    legal = legal_plays(hand, lead_suit=Suit.SPADES, trump=spades_trump)
    assert legal == [left_bower]


def test_may_trump_or_discard_freely_when_void(spades_trump: TrumpCall) -> None:
    hand = [Card(Suit.CLUBS, Rank.NINE), Card(Suit.SPADES, Rank.NINE)]
    legal = legal_plays(hand, lead_suit=Suit.HEARTS, trump=spades_trump)
    assert legal == hand


def test_validate_play_rejects_card_not_in_hand(spades_trump: TrumpCall) -> None:
    hand = [Card(Suit.CLUBS, Rank.NINE)]
    with pytest.raises(IllegalPlayError):
        validate_play(Card(Suit.HEARTS, Rank.ACE), hand, lead_suit=None, trump=spades_trump)


def test_validate_play_rejects_off_suit_when_able_to_follow(spades_trump: TrumpCall) -> None:
    hand = [Card(Suit.HEARTS, Rank.NINE), Card(Suit.CLUBS, Rank.ACE)]
    with pytest.raises(IllegalPlayError):
        validate_play(
            Card(Suit.CLUBS, Rank.ACE), hand, lead_suit=Suit.HEARTS, trump=spades_trump
        )


def test_validate_play_accepts_legal_follow(spades_trump: TrumpCall) -> None:
    hand = [Card(Suit.HEARTS, Rank.NINE), Card(Suit.CLUBS, Rank.ACE)]
    validate_play(Card(Suit.HEARTS, Rank.NINE), hand, lead_suit=Suit.HEARTS, trump=spades_trump)


def test_trick_winner_highest_of_lead_suit_when_no_trump_played(
    spades_trump: TrumpCall,
) -> None:
    trick = [
        TrickPlay(player_id=0, card=Card(Suit.HEARTS, Rank.NINE)),
        TrickPlay(player_id=1, card=Card(Suit.HEARTS, Rank.ACE)),
        TrickPlay(player_id=2, card=Card(Suit.CLUBS, Rank.ACE)),  # off-suit, can't win
        TrickPlay(player_id=3, card=Card(Suit.HEARTS, Rank.KING)),
    ]
    assert determine_trick_winner(trick, spades_trump) == 1


def test_trick_winner_trump_beats_lead_suit(spades_trump: TrumpCall) -> None:
    trick = [
        TrickPlay(player_id=0, card=Card(Suit.HEARTS, Rank.ACE)),
        TrickPlay(player_id=1, card=Card(Suit.SPADES, Rank.NINE)),  # low trump still wins
        TrickPlay(player_id=2, card=Card(Suit.HEARTS, Rank.KING)),
        TrickPlay(player_id=3, card=Card(Suit.CLUBS, Rank.ACE)),
    ]
    assert determine_trick_winner(trick, spades_trump) == 1


def test_trick_winner_left_bower_wins_as_trump(spades_trump: TrumpCall) -> None:
    trick = [
        TrickPlay(player_id=0, card=Card(Suit.SPADES, Rank.KING)),
        TrickPlay(player_id=1, card=Card(Suit.CLUBS, Rank.JACK)),  # left bower
        TrickPlay(player_id=2, card=Card(Suit.SPADES, Rank.ACE)),
        TrickPlay(player_id=3, card=Card(Suit.HEARTS, Rank.NINE)),
    ]
    assert determine_trick_winner(trick, spades_trump) == 1


def test_trick_winner_no_trump_low_mode() -> None:
    low = TrumpCall(mode=TrumpMode.LOW)
    trick = [
        TrickPlay(player_id=0, card=Card(Suit.CLUBS, Rank.NINE)),
        TrickPlay(player_id=1, card=Card(Suit.CLUBS, Rank.ACE)),
        TrickPlay(player_id=2, card=Card(Suit.HEARTS, Rank.KING)),  # off-suit
    ]
    # nine is highest in "low" mode
    assert determine_trick_winner(trick, low) == 0


def test_active_players_normal_bid_is_all_four() -> None:
    bid = Bid(player_id=1, rung=BidRung.SIX)
    assert active_players(bid) == [0, 1, 2, 3]


def test_active_players_alone_excludes_partner() -> None:
    bid = Bid(player_id=1, rung=BidRung.ALONE)
    assert active_players(bid) == [0, 1, 2]  # player 3 is partner of 1, excluded


def test_active_players_moon_also_excludes_partner() -> None:
    # MOON plays the bidder solo too - the swap is the partner's only
    # contribution, same exclusion as ALONE.
    bid = Bid(player_id=1, rung=BidRung.MOON)
    assert active_players(bid) == [0, 1, 2]  # player 3 is partner of 1, excluded


def test_trick_play_order_alone_skips_partner_and_wraps_clockwise() -> None:
    bid = Bid(player_id=1, rung=BidRung.ALONE)
    # leader is player 2; clockwise order 2,3,0,1 but 3 (partner of bidder 1) sits out
    assert trick_play_order(leader_id=2, winning_bid=bid) == [2, 0, 1]


def test_trick_play_order_moon_skips_partner_and_wraps_clockwise() -> None:
    bid = Bid(player_id=1, rung=BidRung.MOON)
    assert trick_play_order(leader_id=2, winning_bid=bid) == [2, 0, 1]
