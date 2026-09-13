from bid_euchre.dealing import swap_moon_card
from bid_euchre.models import Bid, BidRung, Card, HandState, Rank, Suit

import pytest


def _state_with_bid(rung: BidRung, bidder_id: int = 0) -> HandState:
    hands = {
        0: [Card(Suit.CLUBS, Rank.NINE), Card(Suit.CLUBS, Rank.TEN)],
        1: [Card(Suit.HEARTS, Rank.NINE)],
        2: [Card(Suit.SPADES, Rank.NINE), Card(Suit.SPADES, Rank.TEN)],
        3: [Card(Suit.DIAMONDS, Rank.NINE)],
    }
    state = HandState(dealer_id=3, hands=hands)
    state.winning_bid = Bid(player_id=bidder_id, rung=rung)
    return state


def test_swap_moves_cards_between_bidder_and_partner() -> None:
    state = _state_with_bid(BidRung.MOON, bidder_id=0)
    bidder_card = Card(Suit.CLUBS, Rank.NINE)
    partner_card = Card(Suit.SPADES, Rank.NINE)  # player 2 is partner of 0

    swap_moon_card(state, bidder_card, partner_card)

    assert bidder_card not in state.hands[0]
    assert partner_card in state.hands[0]
    assert partner_card not in state.hands[2]
    assert bidder_card in state.hands[2]


def test_swap_rejected_when_bid_is_not_moon() -> None:
    state = _state_with_bid(BidRung.SIX, bidder_id=0)
    with pytest.raises(ValueError):
        swap_moon_card(state, Card(Suit.CLUBS, Rank.NINE), Card(Suit.SPADES, Rank.NINE))


def test_swap_rejected_if_card_not_in_bidders_hand() -> None:
    state = _state_with_bid(BidRung.MOON, bidder_id=0)
    with pytest.raises(ValueError):
        swap_moon_card(
            state, Card(Suit.HEARTS, Rank.NINE), Card(Suit.SPADES, Rank.NINE)
        )


def test_swap_rejected_if_card_not_in_partners_hand() -> None:
    state = _state_with_bid(BidRung.MOON, bidder_id=0)
    with pytest.raises(ValueError):
        swap_moon_card(
            state, Card(Suit.CLUBS, Rank.NINE), Card(Suit.DIAMONDS, Rank.NINE)
        )
