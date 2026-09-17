"""Scoring for a completed hand: numeric-bid scoring, the set penalty, and
moon/alone's point values.
"""

from __future__ import annotations

from .models import TEAM_A, TEAM_B, Bid, BidRung, team_of

# Defaults for a normal-length game - see bid_euchre_server.room.GAME_LENGTHS
# for the other length presets (quick, test) that override these per match.
MOON_POINTS = 12
ALONE_POINTS = 24


def score_hand(
    bid: Bid,
    tricks_won: dict[int, int],
    moon_points: int = MOON_POINTS,
    alone_points: int = ALONE_POINTS,
) -> dict[int, int]:
    """Score one completed hand.

    `tricks_won` maps team_id (see `team_of`) to the number of tricks that
    team won. Returns a {team_id: point_delta} dict to add onto running
    match scores.

    Numeric bids (3-6): if the bidding team took at least as many tricks as
    bid, each team scores one point per trick it actually won (including the
    non-bidding team). If the bidding team fell short, they're "set" — they
    lose points equal to the number they bid, and the non-bidding team still
    scores one point per trick it won.

    Moon/alone: +moon_points/+alone_points if the bidding team won all 6
    tricks, negated if not (set) - the actual values depend on the match's
    game length (see room.GAME_LENGTHS). Either way, the non-bidding team
    still scores one point per trick it managed to take off the bidder, same
    as the numeric-bid set penalty (when the bidder makes it, this is
    naturally 0 since they took all 6).
    """
    bidding_team = team_of(bid.player_id)
    other_team = TEAM_B if bidding_team == TEAM_A else TEAM_A
    bidding_tricks = tricks_won.get(bidding_team, 0)
    other_tricks = tricks_won.get(other_team, 0)

    if bid.rung in (BidRung.MOON, BidRung.ALONE):
        points = moon_points if bid.rung is BidRung.MOON else alone_points
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
