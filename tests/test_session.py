from bid_euchre.models import BidRung, TrumpCall, TrumpMode, partner_of
from bid_euchre.ranking import effective_suit
from bid_euchre.trick import determine_trick_winner, legal_plays
from bid_euchre_server.session import GameSession, Phase

import pytest


def _pass_first_three(session: GameSession) -> int:
    """Pass the first 3 bidders, leaving the (now-stuck) dealer to bid.
    Returns the dealer's player_id.
    """
    for _ in range(3):
        turn = session.bidder_turn
        assert turn is not None
        session.submit_bid(turn, BidRung.PASS)
    return session.state.dealer_id


def _play_current_players_first_legal_card(session: GameSession) -> None:
    player_id = session.player_turn
    assert player_id is not None
    assert session.state.trump is not None
    lead_suit = None
    if session.state.current_trick:
        lead_suit = effective_suit(session.state.current_trick[0].card, session.state.trump)
    card = legal_plays(session.state.hands[player_id], lead_suit, session.state.trump)[0]
    session.play_card(player_id, card)


def _play_out_hand(session: GameSession) -> None:
    """Drive a session through one full hand: dealer is forced to bid THREE,
    calls no-trump high, then plays all 6 tricks with each player's first
    legal card.
    """
    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))

    while session.phase is Phase.PLAYING:
        _play_current_players_first_legal_card(session)


def test_full_hand_lifecycle_returns_to_bidding_with_new_dealer() -> None:
    session = GameSession(target_score=1000)
    starting_dealer = session.state.dealer_id

    _play_out_hand(session)

    assert session.phase is Phase.BIDDING
    assert session.state.dealer_id == (starting_dealer + 1) % 4
    assert len(session.state.hands[0]) == 6  # freshly dealt for the new hand
    assert session.state.tricks == []
    assert session.state.winning_bid is None


def test_bid_out_of_turn_rejected() -> None:
    session = GameSession()
    turn = session.bidder_turn
    assert turn is not None
    wrong_player = (turn + 1) % 4
    with pytest.raises(ValueError):
        session.submit_bid(wrong_player, BidRung.THREE)


def test_stuck_dealer_cannot_pass_via_session() -> None:
    session = GameSession()
    dealer_id = _pass_first_three(session)
    with pytest.raises(ValueError):
        session.submit_bid(dealer_id, BidRung.PASS)


def test_call_trump_before_bidding_done_rejected() -> None:
    session = GameSession()
    with pytest.raises(ValueError):
        session.call_trump(0, TrumpCall(mode=TrumpMode.HIGH))


def test_only_bid_winner_may_call_trump() -> None:
    session = GameSession()
    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    non_winner = (dealer_id + 1) % 4
    with pytest.raises(ValueError):
        session.call_trump(non_winner, TrumpCall(mode=TrumpMode.HIGH))


def test_play_out_of_turn_rejected() -> None:
    session = GameSession()
    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))

    turn = session.player_turn
    assert turn is not None
    wrong_player = (turn + 1) % 4
    assert session.state.trump is not None
    card = legal_plays(session.state.hands[wrong_player], None, session.state.trump)[0]
    with pytest.raises(ValueError):
        session.play_card(wrong_player, card)


def test_illegal_play_not_following_suit_rejected() -> None:
    session = GameSession()
    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))
    assert session.state.trump is not None

    leader = session.player_turn
    assert leader is not None
    lead_card = legal_plays(session.state.hands[leader], None, session.state.trump)[0]
    session.play_card(leader, lead_card)
    lead_suit = effective_suit(lead_card, session.state.trump)

    next_player = session.player_turn
    assert next_player is not None
    hand = session.state.hands[next_player]
    can_follow = any(effective_suit(c, session.state.trump) == lead_suit for c in hand)
    off_suit_cards = [c for c in hand if effective_suit(c, session.state.trump) != lead_suit]

    if can_follow and off_suit_cards:
        with pytest.raises(ValueError):
            session.play_card(next_player, off_suit_cards[0])


def test_game_over_when_target_score_reached() -> None:
    session = GameSession(target_score=1)  # trivially low target
    _play_out_hand(session)
    assert session.phase is Phase.GAME_OVER


def test_alone_bid_excludes_partner_from_trick_turns() -> None:
    session = GameSession()
    order = [session.bidder_turn]
    assert order[0] is not None
    bidder_id = order[0]

    session.submit_bid(bidder_id, BidRung.ALONE)
    for _ in range(3):
        turn = session.bidder_turn
        assert turn is not None
        session.submit_bid(turn, BidRung.PASS)

    assert session.state.winning_bid is not None
    assert session.state.winning_bid.player_id == bidder_id

    session.call_trump(bidder_id, TrumpCall(mode=TrumpMode.HIGH))

    excluded = partner_of(bidder_id)
    assert excluded not in session._trick_order  # noqa: SLF001
    assert len(session._trick_order) == 3  # noqa: SLF001


def test_legal_bids_excludes_pass_for_stuck_dealer_and_empty_outside_bidding() -> None:
    session = GameSession()
    assert BidRung.PASS in session.legal_bids
    assert BidRung.THREE in session.legal_bids

    dealer_id = _pass_first_three(session)
    assert session.bidder_turn == dealer_id
    assert BidRung.PASS not in session.legal_bids
    assert BidRung.THREE in session.legal_bids

    session.submit_bid(dealer_id, BidRung.THREE)
    assert session.legal_bids == []  # no longer the bidding phase


def test_legal_bids_only_allows_rungs_above_current_high() -> None:
    session = GameSession()
    turn = session.bidder_turn
    assert turn is not None
    session.submit_bid(turn, BidRung.FOUR)

    assert BidRung.THREE not in session.legal_bids
    assert BidRung.FOUR not in session.legal_bids
    assert BidRung.FIVE in session.legal_bids
    assert BidRung.PASS in session.legal_bids


def test_legal_plays_matches_hand_when_leading_and_empty_outside_playing() -> None:
    session = GameSession()
    assert session.legal_plays == []  # bidding phase, not playing yet

    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))

    leader = session.player_turn
    assert leader is not None
    assert set(session.legal_plays) == set(session.state.hands[leader])


def test_legal_plays_restricted_to_lead_suit_when_able_to_follow() -> None:
    session = GameSession()
    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))
    assert session.state.trump is not None

    leader = session.player_turn
    assert leader is not None
    lead_card = legal_plays(session.state.hands[leader], None, session.state.trump)[0]
    session.play_card(leader, lead_card)
    lead_suit = effective_suit(lead_card, session.state.trump)

    next_player = session.player_turn
    assert next_player is not None
    expected = legal_plays(session.state.hands[next_player], lead_suit, session.state.trump)
    assert set(session.legal_plays) == set(expected)


def test_last_trick_winner_none_until_a_trick_completes_then_matches_the_actual_winner() -> None:
    session = GameSession()
    assert session.last_trick_winner is None

    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))
    assert session.state.trump is not None
    assert session.last_trick_winner is None  # trump just called, no trick played yet

    trick_order = list(session._trick_order)  # noqa: SLF001
    for _ in trick_order:
        _play_current_players_first_legal_card(session)

    expected_winner = determine_trick_winner(session.state.tricks[-1], session.state.trump)
    assert session.last_trick_winner == expected_winner


def test_last_trick_winner_persists_into_next_bidding_then_resets_on_call_trump() -> None:
    """last_trick_winner deliberately survives into the next hand's BIDDING
    phase (so a client can still show "you won the last trick" for the
    final trick of the hand that just ended) and only clears once the new
    hand's call_trump actually starts fresh trick play.
    """
    session = GameSession(target_score=1000)
    _play_out_hand(session)  # plays a full hand; the final trick's winner is recorded

    assert session.phase is Phase.BIDDING
    assert session.last_trick_winner is not None

    dealer_id = _pass_first_three(session)
    session.submit_bid(dealer_id, BidRung.THREE)
    session.call_trump(dealer_id, TrumpCall(mode=TrumpMode.HIGH))
    assert session.last_trick_winner is None


def test_left_of_dealer_leads_first_trick_even_when_not_the_bid_winner() -> None:
    """CLAUDE.md: the player left of the dealer leads the first trick -
    the same seat that led off bidding - regardless of who won the bid.
    Other tests happen to have the bid winner coincide with left-of-dealer
    (or the dealer), which would pass even if the code wrongly used the bid
    winner instead of dealer position. This test picks a winner who is
    neither, to actually distinguish the two rules.
    """
    session = GameSession()
    dealer_id = session.state.dealer_id
    assert dealer_id == 0
    left_of_dealer = 1

    session.submit_bid(1, BidRung.PASS)
    session.submit_bid(2, BidRung.THREE)  # player 2: neither dealer nor left of dealer
    session.submit_bid(3, BidRung.PASS)
    session.submit_bid(0, BidRung.PASS)  # dealer may pass; a bid already stands

    assert session.state.winning_bid is not None
    assert session.state.winning_bid.player_id == 2

    session.call_trump(2, TrumpCall(mode=TrumpMode.HIGH))

    assert session.player_turn == left_of_dealer
    assert session.player_turn != dealer_id
    assert session.player_turn != 2  # not the bid winner


def test_moon_swap_allowed_before_first_trick_then_locked_out() -> None:
    session = GameSession()
    bidder_id = session.bidder_turn
    assert bidder_id is not None

    session.submit_bid(bidder_id, BidRung.MOON)
    for _ in range(3):
        turn = session.bidder_turn
        assert turn is not None
        session.submit_bid(turn, BidRung.PASS)

    session.call_trump(bidder_id, TrumpCall(mode=TrumpMode.HIGH))

    partner_id = partner_of(bidder_id)
    bidder_card = session.state.hands[bidder_id][0]
    partner_card = session.state.hands[partner_id][0]
    session.swap_moon_card(bidder_id, bidder_card, partner_card)
    assert partner_card in session.state.hands[bidder_id]

    _play_current_players_first_legal_card(session)

    with pytest.raises(ValueError):
        session.swap_moon_card(
            bidder_id, session.state.hands[bidder_id][0], session.state.hands[partner_id][0]
        )
