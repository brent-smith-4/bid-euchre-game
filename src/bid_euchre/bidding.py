"""Bidding: legal-bid checks, the stuck-dealer rule, and full-round resolution."""

from __future__ import annotations

from .models import Bid, BidRung, NUM_PLAYERS


def bid_order(dealer_id: int) -> list[int]:
    """Turn order for a bidding round: starts left of dealer, ends on the dealer."""
    return [(dealer_id + offset) % NUM_PLAYERS for offset in range(1, NUM_PLAYERS + 1)]


def is_legal_bid(rung: BidRung, current_high: BidRung, is_forced: bool) -> bool:
    """Whether `rung` is a legal next bid.

    A bid is legal if it's a pass (when not forced) or strictly outranks the
    current high bid on the ladder — players may jump rungs freely. A forced
    (stuck-dealer) bid may not pass and must clear the ladder's THREE floor,
    which is implied by "strictly higher than PASS" since the dealer is only
    ever forced when everyone else has passed.
    """
    if is_forced:
        return rung != BidRung.PASS and rung.value > current_high.value
    return rung == BidRung.PASS or rung.value > current_high.value


def resolve_bidding_round(dealer_id: int, bids: list[Bid]) -> Bid:
    """Validate one full round of bidding (one bid per player, in turn order)
    and return the winning bid.

    Raises ValueError if a bid is out of turn or illegal against the ladder.
    """
    order = bid_order(dealer_id)
    if len(bids) != NUM_PLAYERS:
        raise ValueError(f"expected exactly {NUM_PLAYERS} bids, got {len(bids)}")

    current_high = BidRung.PASS
    winning_bid: Bid | None = None

    for seat_index, expected_player in enumerate(order):
        bid = bids[seat_index]
        if bid.player_id != expected_player:
            raise ValueError(
                f"bid out of turn: expected player {expected_player}, got {bid.player_id}"
            )

        is_dealer_turn = seat_index == NUM_PLAYERS - 1
        is_forced = is_dealer_turn and current_high == BidRung.PASS

        if not is_legal_bid(bid.rung, current_high, is_forced):
            raise ValueError(
                f"illegal bid {bid.rung.name} by player {bid.player_id} "
                f"(current high: {current_high.name}, forced: {is_forced})"
            )

        if bid.rung != BidRung.PASS:
            current_high = bid.rung
            winning_bid = bid

    # Invariant: the dealer is forced to bid whenever the first three pass,
    # so a winning bid always exists (no redeal-on-all-pass path).
    assert winning_bid is not None
    return winning_bid
