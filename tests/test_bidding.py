from bid_euchre.bidding import bid_order, is_legal_bid, resolve_bidding_round
from bid_euchre.models import Bid, BidRung

import pytest


def test_bid_order_starts_left_of_dealer_and_ends_on_dealer() -> None:
    assert bid_order(dealer_id=0) == [1, 2, 3, 0]
    assert bid_order(dealer_id=2) == [3, 0, 1, 2]


def test_pass_is_legal_when_not_forced() -> None:
    assert is_legal_bid(BidRung.PASS, current_high=BidRung.THREE, is_forced=False)


def test_pass_is_illegal_when_forced() -> None:
    assert not is_legal_bid(BidRung.PASS, current_high=BidRung.PASS, is_forced=True)


def test_can_jump_rungs_freely() -> None:
    assert is_legal_bid(BidRung.SIX, current_high=BidRung.THREE, is_forced=False)


def test_bid_must_strictly_exceed_current_high() -> None:
    assert not is_legal_bid(BidRung.FOUR, current_high=BidRung.FOUR, is_forced=False)
    assert not is_legal_bid(BidRung.THREE, current_high=BidRung.FOUR, is_forced=False)


def test_resolve_bidding_round_normal_case() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=1, rung=BidRung.THREE),
        Bid(player_id=2, rung=BidRung.PASS),
        Bid(player_id=3, rung=BidRung.FIVE),
        Bid(player_id=0, rung=BidRung.PASS),
    ]
    winner = resolve_bidding_round(dealer_id, bids)
    assert winner == Bid(player_id=3, rung=BidRung.FIVE)


def test_stuck_dealer_forced_to_bid_at_least_three() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=1, rung=BidRung.PASS),
        Bid(player_id=2, rung=BidRung.PASS),
        Bid(player_id=3, rung=BidRung.PASS),
        Bid(player_id=0, rung=BidRung.THREE),
    ]
    winner = resolve_bidding_round(dealer_id, bids)
    assert winner == Bid(player_id=0, rung=BidRung.THREE)


def test_stuck_dealer_may_bid_higher_than_minimum() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=1, rung=BidRung.PASS),
        Bid(player_id=2, rung=BidRung.PASS),
        Bid(player_id=3, rung=BidRung.PASS),
        Bid(player_id=0, rung=BidRung.ALONE),
    ]
    winner = resolve_bidding_round(dealer_id, bids)
    assert winner == Bid(player_id=0, rung=BidRung.ALONE)


def test_stuck_dealer_cannot_pass() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=1, rung=BidRung.PASS),
        Bid(player_id=2, rung=BidRung.PASS),
        Bid(player_id=3, rung=BidRung.PASS),
        Bid(player_id=0, rung=BidRung.PASS),
    ]
    with pytest.raises(ValueError):
        resolve_bidding_round(dealer_id, bids)


def test_bid_out_of_turn_raises() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=2, rung=BidRung.THREE),  # player 1 should bid first
        Bid(player_id=1, rung=BidRung.PASS),
        Bid(player_id=3, rung=BidRung.PASS),
        Bid(player_id=0, rung=BidRung.PASS),
    ]
    with pytest.raises(ValueError):
        resolve_bidding_round(dealer_id, bids)


def test_bid_that_does_not_exceed_current_high_raises() -> None:
    dealer_id = 0
    bids = [
        Bid(player_id=1, rung=BidRung.FIVE),
        Bid(player_id=2, rung=BidRung.FOUR),  # doesn't exceed FIVE
        Bid(player_id=3, rung=BidRung.PASS),
        Bid(player_id=0, rung=BidRung.PASS),
    ]
    with pytest.raises(ValueError):
        resolve_bidding_round(dealer_id, bids)


def test_wrong_number_of_bids_raises() -> None:
    dealer_id = 0
    bids = [Bid(player_id=1, rung=BidRung.THREE)]
    with pytest.raises(ValueError):
        resolve_bidding_round(dealer_id, bids)
