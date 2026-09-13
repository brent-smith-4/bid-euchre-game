"""Scoring for a completed hand: numeric-bid scoring, the set penalty, and
moon/alone's fixed point values.
"""

from __future__ import annotations

from .models import TEAM_A, TEAM_B, Bid, BidRung, team_of

MOON_POINTS = 12
ALONE_POINTS = 24


def score_hand(bid: Bid, tricks_won: dict[int, int]) -> dict[int, int]:
    """Score one completed hand.

    `tricks_won` maps team_id (see `team_of`) to the number of tricks that
    team won. Returns a {team_id: point_delta} dict to add onto running
    match scores.

    Numeric bids (3-6): if the bidding team took at least as many tricks as
    bid, each team scores one point per trick it actually won (including the
    non-bidding team). If the bidding team fell short, they're "set" — they
    lose points equal to the number they bid, and the non-bidding team still
    scores one point per trick it won.

    Moon/alone: +12/+24 if the bidding team won all 6 tricks, -12/-24 if not
    (set). Either way, the non-bidding team still scores one point per trick
    it managed to take off the bidder, same as the numeric-bid set penalty
    (when the bidder makes it, this is naturally 0 since they took all 6).
    """
    bidding_team = team_of(bid.player_id)
    other_team = TEAM_B if bidding_team == TEAM_A else TEAM_A
    bidding_tricks = tricks_won.get(bidding_team, 0)
    other_tricks = tricks_won.get(other_team, 0)

    if bid.rung in (BidRung.MOON, BidRung.ALONE):
        points = MOON_POINTS if bid.rung is BidRung.MOON else ALONE_POINTS
        made = bidding_tricks == 6
        return {bidding_team: points if made else -points, other_team: other_tricks}

    bid_amount = bid.rung.value
    if bidding_tricks >= bid_amount:
        return {bidding_team: bidding_tricks, other_team: other_tricks}
    return {bidding_team: -bid_amount, other_team: other_tricks}


def apply_hand_score(scores: dict[int, int], deltas: dict[int, int]) -> dict[int, int]:
    """Add a hand's score deltas onto running match scores in place, and
    return them (matches HandState.scores as CLAUDE.md's "running scores").
    """
    for team_id, delta in deltas.items():
        scores[team_id] = scores.get(team_id, 0) + delta
    return scores
