"""JSON (de)serialization between wire messages and bid_euchre domain objects,
and the personalized state view sent to each connected client.
"""

from __future__ import annotations

from typing import Any

from bid_euchre.models import Bid, Card, Rank, Suit, TrickPlay, TrumpCall, TrumpMode
from bid_euchre_server.room import Room, TeamMeta
from bid_euchre_server.session import GameSession


def card_to_json(card: Card) -> dict[str, str]:
    return {"suit": card.suit.name, "rank": card.rank.name}


def card_from_json(data: dict[str, Any]) -> Card:
    return Card(suit=Suit[data["suit"]], rank=Rank[data["rank"]])


def bid_to_json(bid: Bid) -> dict[str, Any]:
    return {"player_id": bid.player_id, "rung": bid.rung.name}


def trump_call_to_json(trump: TrumpCall) -> dict[str, Any]:
    return {"mode": trump.mode.name, "suit": trump.suit.name if trump.suit else None}


def trump_call_from_json(data: dict[str, Any]) -> TrumpCall:
    suit_name = data.get("suit")
    return TrumpCall(mode=TrumpMode[data["mode"]], suit=Suit[suit_name] if suit_name else None)


def trick_play_to_json(play: TrickPlay) -> dict[str, Any]:
    return {"player_id": play.player_id, "card": card_to_json(play.card)}


def team_to_json(team: TeamMeta) -> dict[str, Any]:
    return {"color": team.color, "name": team.name}


def build_lobby_view(room: Room, viewer_id: int) -> dict[str, Any]:
    """The lobby payload sent to one specific connected player, while
    `room.status` is still LOBBY.
    """
    return {
        "type": "lobby_state",
        "room_code": room.code,
        "your_player_id": viewer_id,
        "host_id": room.host_id,
        "target_score": room.target_score,
        "players": dict(room.player_team),
        "teams": {
            team_id: {
                **team_to_json(team),
                "naming_rights_holder": room.naming_rights_holder(team_id),
            }
            for team_id, team in room.teams.items()
        },
        "bots": sorted(room.bot_ids),
    }


def build_state_view(
    session: GameSession, viewer_id: int, teams: dict[int, TeamMeta], bots: set[int], is_host: bool
) -> dict[str, Any]:
    """The state payload sent to one specific player. Only `viewer_id`'s own
    hand is included in full — everyone else's hand is just a card count, so
    the server never leaks hidden information to the wrong client.
    """
    state = session.state
    return {
        "type": "state",
        "phase": session.phase.name,
        "teams": {team_id: team_to_json(team) for team_id, team in teams.items()},
        "your_player_id": viewer_id,
        "dealer_id": state.dealer_id,
        "your_hand": [card_to_json(c) for c in state.hands[viewer_id]],
        "hand_sizes": {pid: len(hand) for pid, hand in state.hands.items()},
        "bid_history": [bid_to_json(b) for b in state.bid_history],
        "winning_bid": bid_to_json(state.winning_bid) if state.winning_bid else None,
        "trump": trump_call_to_json(state.trump) if state.trump else None,
        "tricks_completed": len(state.tricks),
        "tricks_won": session.tricks_won_by_player,
        "last_trick_winner": session.last_trick_winner,
        "last_trick": (
            [trick_play_to_json(p) for p in session.last_trick_cards] if session.last_trick_cards else None
        ),
        "current_trick": [trick_play_to_json(p) for p in state.current_trick],
        "scores": dict(state.scores),
        "target_score": session.target_score,
        "bidder_turn": session.bidder_turn,
        "player_turn": session.player_turn,
        "moon_swap_turn": session.moon_swap_turn,
        "legal_bids": (
            [rung.name for rung in session.legal_bids] if session.bidder_turn == viewer_id else []
        ),
        "legal_plays": (
            [card_to_json(c) for c in session.legal_plays] if session.player_turn == viewer_id else []
        ),
        "bots": sorted(bots),
        "is_host": is_host,
    }
