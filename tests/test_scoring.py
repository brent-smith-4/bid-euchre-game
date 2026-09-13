from bid_euchre.models import Bid, BidRung
from bid_euchre.scoring import apply_hand_score, score_hand


def test_bidding_team_makes_bid_scores_tricks_taken() -> None:
    bid = Bid(player_id=0, rung=BidRung.FOUR)  # team 0
    deltas = score_hand(bid, tricks_won={0: 4, 1: 2})
    assert deltas == {0: 4, 1: 2}


def test_bidding_team_exceeds_bid_scores_actual_tricks() -> None:
    bid = Bid(player_id=0, rung=BidRung.THREE)
    deltas = score_hand(bid, tricks_won={0: 5, 1: 1})
    assert deltas == {0: 5, 1: 1}


def test_bidding_team_set_loses_points_equal_to_bid() -> None:
    bid = Bid(player_id=1, rung=BidRung.SIX)  # team 1
    deltas = score_hand(bid, tricks_won={1: 3, 0: 3})
    assert deltas == {1: -6, 0: 3}


def test_moon_made_scores_twelve() -> None:
    bid = Bid(player_id=0, rung=BidRung.MOON)
    deltas = score_hand(bid, tricks_won={0: 6, 1: 0})
    assert deltas == {0: 12, 1: 0}


def test_moon_set_loses_twelve_opponent_scores_tricks() -> None:
    bid = Bid(player_id=0, rung=BidRung.MOON)
    deltas = score_hand(bid, tricks_won={0: 4, 1: 2})
    assert deltas == {0: -12, 1: 2}


def test_alone_made_scores_twenty_four() -> None:
    bid = Bid(player_id=3, rung=BidRung.ALONE)  # team 1
    deltas = score_hand(bid, tricks_won={1: 6, 0: 0})
    assert deltas == {1: 24, 0: 0}


def test_alone_set_loses_twenty_four_opponent_scores_tricks() -> None:
    bid = Bid(player_id=3, rung=BidRung.ALONE)
    deltas = score_hand(bid, tricks_won={1: 2, 0: 4})
    assert deltas == {1: -24, 0: 4}


def test_scores_can_go_negative_across_hands() -> None:
    running = {0: 1, 1: 0}
    set_bid = Bid(player_id=1, rung=BidRung.SIX)
    deltas = score_hand(set_bid, tricks_won={1: 1, 0: 5})
    apply_hand_score(running, deltas)
    assert running == {0: 6, 1: -6}


def test_apply_hand_score_accumulates_across_multiple_hands() -> None:
    running: dict[int, int] = {0: 0, 1: 0}
    apply_hand_score(running, {0: 4, 1: 2})
    apply_hand_score(running, {0: -6, 1: 3})
    assert running == {0: -2, 1: 5}
