"""GameSession: a stateful orchestrator for one live in-memory game.

This is the "game loop" that ties the pure bid_euchre rules-engine functions
together with turn tracking across a full match (many hands, dealer
rotation, running score, win condition). It has no networking knowledge —
main.py adapts it to WebSocket messages. All state transitions raise
ValueError (or IllegalPlayError, a ValueError subclass) on any illegal
action; the caller is responsible for turning that into a client-facing
error message.
"""

from __future__ import annotations

from enum import Enum, auto

from bid_euchre.bidding import bid_order, is_legal_bid
from bid_euchre.dealing import deal_new_hand, swap_moon_card
from bid_euchre.models import (
    NUM_PLAYERS,
    TEAM_A,
    TEAM_B,
    Bid,
    BidRung,
    Card,
    HandState,
    TrickPlay,
    TrumpCall,
    team_of,
)
from bid_euchre.ranking import effective_suit
from bid_euchre.scoring import apply_hand_score, score_hand
from bid_euchre.trick import determine_trick_winner, trick_play_order, validate_play
from bid_euchre.trick import legal_plays as compute_legal_plays


class Phase(Enum):
    BIDDING = auto()
    CALLING_TRUMP = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class GameSession:
    def __init__(self, target_score: int = 52, first_dealer_id: int = 0) -> None:
        self.target_score = target_score
        self.phase = Phase.BIDDING
        self.state: HandState = deal_new_hand(first_dealer_id)
        self._bid_order = bid_order(self.state.dealer_id)
        self._bid_turn_index = 0
        self._current_high = BidRung.PASS
        self._tricks_won = {TEAM_A: 0, TEAM_B: 0}
        self._trick_order: list[int] = []
        self._trick_turn_index = 0
        self._last_trick_winner: int | None = None

    # -- read-only views for the networking layer -------------------------

    @property
    def bidder_turn(self) -> int | None:
        if self.phase is not Phase.BIDDING:
            return None
        return self._bid_order[self._bid_turn_index]

    @property
    def player_turn(self) -> int | None:
        if self.phase is not Phase.PLAYING:
            return None
        return self._trick_order[self._trick_turn_index]

    @property
    def last_trick_winner(self) -> int | None:
        """Winner of the most recently completed trick in the CURRENT hand,
        or None if no trick has finished yet this hand. Lets clients show a
        "you won/lost the trick" notice without duplicating
        determine_trick_winner's ranking logic themselves.
        """
        return self._last_trick_winner

    @property
    def legal_bids(self) -> list[BidRung]:
        """Bid rungs the current bidder may legally submit right now, for
        client-side button enable/disable. Reuses `is_legal_bid` directly
        rather than duplicating the ladder rules — see the same reasoning in
        `submit_bid`.
        """
        if self.phase is not Phase.BIDDING:
            return []

        is_forced = self._bid_turn_index == NUM_PLAYERS - 1 and self._current_high is BidRung.PASS
        return [
            rung
            for rung in BidRung
            if is_legal_bid(rung, self._current_high, is_forced)
        ]

    @property
    def legal_plays(self) -> list[Card]:
        """Cards the current player may legally play right now, from their
        own hand, for client-side card greying. Reuses `legal_plays` from
        `bid_euchre.trick` rather than duplicating follow-suit rules — see
        the same reasoning in `play_card`.
        """
        if self.phase is not Phase.PLAYING:
            return []

        assert self.state.trump is not None
        player_id = self._trick_order[self._trick_turn_index]
        hand = self.state.hands[player_id]
        lead_suit = (
            effective_suit(self.state.current_trick[0].card, self.state.trump)
            if self.state.current_trick
            else None
        )
        return compute_legal_plays(hand, lead_suit, self.state.trump)

    # -- bidding ------------------------------------------------------------

    def submit_bid(self, player_id: int, rung: BidRung) -> None:
        if self.phase is not Phase.BIDDING:
            raise ValueError("not in the bidding phase")

        expected_player = self._bid_order[self._bid_turn_index]
        if player_id != expected_player:
            raise ValueError(f"not player {player_id}'s turn to bid")

        is_dealer_turn = self._bid_turn_index == NUM_PLAYERS - 1
        is_forced = is_dealer_turn and self._current_high is BidRung.PASS
        if not is_legal_bid(rung, self._current_high, is_forced):
            raise ValueError(f"illegal bid {rung.name}")

        self.state.bid_history.append(Bid(player_id=player_id, rung=rung))
        if rung is not BidRung.PASS:
            self._current_high = rung
            self.state.winning_bid = Bid(player_id=player_id, rung=rung)

        self._bid_turn_index += 1
        if self._bid_turn_index == NUM_PLAYERS:
            # Guaranteed non-None: the stuck dealer can't pass, so some bid won.
            assert self.state.winning_bid is not None
            self.phase = Phase.CALLING_TRUMP

    # -- trump call -----------------------------------------------------

    def call_trump(self, player_id: int, trump: TrumpCall) -> None:
        if self.phase is not Phase.CALLING_TRUMP:
            raise ValueError("not in the trump-calling phase")

        winning_bid = self.state.winning_bid
        assert winning_bid is not None
        if player_id != winning_bid.player_id:
            raise ValueError("only the bid winner calls trump")

        self.state.trump = trump
        self._tricks_won = {TEAM_A: 0, TEAM_B: 0}
        self._last_trick_winner = None
        # The first trick is led by the player left of the dealer - the same
        # seat that led off bidding (self._bid_order[0]) - not by the bid
        # winner. If that seat is the sitting-out partner of an ALONE bid,
        # trick_play_order's active-player filter naturally skips them and
        # the next active player clockwise leads instead.
        self._trick_order = trick_play_order(self._bid_order[0], winning_bid)
        self._trick_turn_index = 0
        self.phase = Phase.PLAYING

    def swap_moon_card(self, player_id: int, card_from_bidder: Card, card_from_partner: Card) -> None:
        if self.phase is not Phase.PLAYING:
            raise ValueError("can only swap after trump is called")
        if self.state.tricks or self.state.current_trick:
            raise ValueError("the moon swap must happen before the first trick")

        winning_bid = self.state.winning_bid
        assert winning_bid is not None
        if player_id != winning_bid.player_id:
            raise ValueError("only the bidder can initiate the moon swap")

        swap_moon_card(self.state, card_from_bidder, card_from_partner)

    # -- trick play -----------------------------------------------------

    def play_card(self, player_id: int, card: Card) -> None:
        if self.phase is not Phase.PLAYING:
            raise ValueError("not in the trick-playing phase")

        expected_player = self._trick_order[self._trick_turn_index]
        if player_id != expected_player:
            raise ValueError(f"not player {player_id}'s turn to play")

        assert self.state.trump is not None
        hand = self.state.hands[player_id]
        lead_suit = (
            effective_suit(self.state.current_trick[0].card, self.state.trump)
            if self.state.current_trick
            else None
        )
        validate_play(card, hand, lead_suit, self.state.trump)

        hand.remove(card)
        self.state.current_trick.append(TrickPlay(player_id=player_id, card=card))
        self._trick_turn_index += 1

        if self._trick_turn_index < len(self._trick_order):
            return

        winner_id = determine_trick_winner(self.state.current_trick, self.state.trump)
        self.state.tricks.append(self.state.current_trick)
        self.state.current_trick = []
        self._tricks_won[team_of(winner_id)] += 1
        self._last_trick_winner = winner_id

        assert self.state.winning_bid is not None
        if len(self.state.tricks) == 6:
            self._finish_hand()
        else:
            self._trick_order = trick_play_order(winner_id, self.state.winning_bid)
            self._trick_turn_index = 0

    # -- hand / match completion -----------------------------------------

    def _finish_hand(self) -> None:
        assert self.state.winning_bid is not None
        deltas = score_hand(self.state.winning_bid, self._tricks_won)
        apply_hand_score(self.state.scores, deltas)

        if any(score >= self.target_score for score in self.state.scores.values()):
            self.phase = Phase.GAME_OVER
            return

        next_dealer_id = (self.state.dealer_id + 1) % NUM_PLAYERS
        self.state = deal_new_hand(next_dealer_id, scores=self.state.scores)
        self._bid_order = bid_order(next_dealer_id)
        self._bid_turn_index = 0
        self._current_high = BidRung.PASS
        self.phase = Phase.BIDDING
