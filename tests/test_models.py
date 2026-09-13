from bid_euchre.models import BidRung, Suit, TrumpCall, TrumpMode, partner_of, team_of

import pytest


def test_bid_rung_ladder_order() -> None:
    ladder = [
        BidRung.PASS,
        BidRung.THREE,
        BidRung.FOUR,
        BidRung.FIVE,
        BidRung.SIX,
        BidRung.MOON,
        BidRung.ALONE,
    ]
    values = [rung.value for rung in ladder]
    assert values == sorted(values)


def test_numeric_rung_values_match_bid_amount() -> None:
    assert BidRung.THREE.value == 3
    assert BidRung.SIX.value == 6


@pytest.mark.parametrize(
    "player_id,expected_team",
    [(0, 0), (1, 1), (2, 0), (3, 1)],
)
def test_team_of_fixed_partnerships(player_id: int, expected_team: int) -> None:
    assert team_of(player_id) == expected_team


@pytest.mark.parametrize(
    "player_id,expected_partner",
    [(0, 2), (2, 0), (1, 3), (3, 1)],
)
def test_partner_of(player_id: int, expected_partner: int) -> None:
    assert partner_of(player_id) == expected_partner


def test_trump_call_suit_requires_suit() -> None:
    with pytest.raises(ValueError):
        TrumpCall(mode=TrumpMode.SUIT, suit=None)


def test_trump_call_no_trump_rejects_suit() -> None:
    with pytest.raises(ValueError):
        TrumpCall(mode=TrumpMode.HIGH, suit=Suit.CLUBS)
    with pytest.raises(ValueError):
        TrumpCall(mode=TrumpMode.LOW, suit=Suit.SPADES)


def test_trump_call_valid_constructions() -> None:
    TrumpCall(mode=TrumpMode.SUIT, suit=Suit.HEARTS)
    TrumpCall(mode=TrumpMode.HIGH)
    TrumpCall(mode=TrumpMode.LOW)
