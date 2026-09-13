import random

from bid_euchre.dealing import build_deck, deal_hands, deal_new_hand
from bid_euchre.models import NUM_PLAYERS


def test_build_deck_has_24_unique_cards() -> None:
    deck = build_deck()
    assert len(deck) == 24
    assert len(set(deck)) == 24


def test_deal_hands_gives_six_cards_each_no_overlap() -> None:
    deck = build_deck()
    hands = deal_hands(deck)
    assert set(hands.keys()) == {0, 1, 2, 3}
    all_dealt: list[object] = []
    for player_id in range(NUM_PLAYERS):
        assert len(hands[player_id]) == 6
        all_dealt.extend(hands[player_id])
    assert len(set(all_dealt)) == 24


def test_deal_new_hand_is_shuffled_deterministically_with_seeded_rng() -> None:
    state_a = deal_new_hand(dealer_id=0, rng=random.Random(42))
    state_b = deal_new_hand(dealer_id=0, rng=random.Random(42))
    assert state_a.hands == state_b.hands


def test_deal_new_hand_carries_forward_scores() -> None:
    previous_scores = {0: 10, 1: 4}
    state = deal_new_hand(dealer_id=1, scores=previous_scores)
    assert state.scores == previous_scores
    # mutating the returned state shouldn't mutate the caller's dict
    state.scores[0] = 999
    assert previous_scores[0] == 10


def test_deal_new_hand_defaults_scores_to_zero() -> None:
    state = deal_new_hand(dealer_id=0)
    assert state.scores == {0: 0, 1: 0}
