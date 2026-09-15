"""FastAPI app serving many concurrent room-code based games over WebSockets.

Each Room is fully isolated (its own ConnectionManager, its own GameSession
once started) - main.py's only job is translating WebSocket JSON messages
into Room/GameSession calls and broadcasting the result. All game-state
mutation still goes through GameSession (the sole source of truth for an
in-progress hand); Room is the sole source of truth for lobby state
(teams/colors/names/host) and for which room a given connection belongs to.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from bid_euchre.bidding import bid_order
from bid_euchre.models import BidRung
from bid_euchre_server.bot import choose_bid, choose_card_to_play, choose_moon_swap_card, choose_trump
from bid_euchre_server.connection_manager import GameFullError
from bid_euchre_server.protocol import build_lobby_view, build_state_view, card_from_json, trump_call_from_json
from bid_euchre_server.rate_limit import RateLimiter
from bid_euchre_server.room import Room, RoomRegistry, RoomStatus
from bid_euchre_server.session import GameSession, Phase

app = FastAPI()
# Dev-only: the Vite dev server runs on a different origin than uvicorn.
# Update this before deploying anywhere the frontend isn't localhost:5173.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

registry = RoomRegistry()
room_creation_limiter = RateLimiter(max_calls=5, window_seconds=60)

# Artificial "thinking" delays so bot turns don't just flash by instantly.
# Module-level (not constants) so tests can zero them out for speed - see
# test_main.py's reset_registry fixture. Bids escalate per consecutive bot
# in the same cascade (BID_DELAY_INCREMENT per additional bid) so a run of
# bot bids doesn't feel like they all fired at once; trump calls and the
# moon swap card reuse ACTION_DELAY_RANGE; card plays are a fixed
# CARD_PLAY_DELAY. TRICK_CLEAR_DELAY matches the frontend's
# useTrickDisplay HOLD_MS (2000ms) - a bot leading a brand new trick waits
# for that long BEFORE its own CARD_PLAY_DELAY even starts counting, so its
# "thinking" timer doesn't start until the previous trick has actually
# finished being shown, not overlapping with it.
BID_DELAY_RANGE = (1.0, 2.0)
BID_DELAY_INCREMENT = 1.0
ACTION_DELAY_RANGE = (0.5, 1.5)
CARD_PLAY_DELAY = 1.5
TRICK_CLEAR_DELAY = 2.0


@app.post("/rooms")
async def create_room(request: Request) -> dict[str, str]:
    client_host = request.client.host if request.client else "unknown"
    if not room_creation_limiter.allow(client_host):
        raise HTTPException(status_code=429, detail="too many rooms created, try again in a minute")
    room = registry.create_room()
    return {"room_code": room.code}


def handle_message(active_session: GameSession, player_id: int, message: dict[str, Any]) -> None:
    msg_type = message.get("type")

    if msg_type == "bid":
        active_session.submit_bid(player_id, BidRung[message["rung"]])
    elif msg_type == "call_trump":
        swap_out_card = card_from_json(message["swap_out_card"]) if message.get("swap_out_card") else None
        active_session.call_trump(player_id, trump_call_from_json(message), swap_out_card)
    elif msg_type == "submit_moon_swap_card":
        active_session.submit_moon_swap_card(player_id, card_from_json(message["card"]))
    elif msg_type == "play_card":
        active_session.play_card(player_id, card_from_json(message["card"]))
    else:
        raise ValueError(f"unknown message type: {msg_type!r}")


def handle_lobby_message(room: Room, player_id: int, message: dict[str, Any]) -> None:
    msg_type = message.get("type")

    if msg_type == "swap_team":
        room.swap_team(player_id, message["with_player_id"])
    elif msg_type == "set_team_color":
        room.set_team_color(player_id, message["team"], message["color"])
    elif msg_type == "set_team_name":
        room.set_team_name(player_id, message["team"], message["name"])
    elif msg_type == "set_target_score":
        room.set_target_score(player_id, message["value"])
    elif msg_type == "start_game":
        room.start_game(player_id)
    elif msg_type == "add_bot":
        room.add_bot(player_id)
    elif msg_type == "remove_bot":
        room.remove_bot(player_id, message["bot_id"])
    else:
        raise ValueError(f"unknown message type: {msg_type!r}")


def _current_turn_game_id(session: GameSession) -> int | None:
    """Whose turn it is right now, in GameSession player_id space. Only
    CALLING_TRUMP has no dedicated turn property (only the bid winner acts,
    via `winning_bid.player_id`) - everything else already exposes one.
    """
    if session.phase is Phase.CALLING_TRUMP:
        assert session.state.winning_bid is not None
        return session.state.winning_bid.player_id
    if session.bidder_turn is not None:
        return session.bidder_turn
    if session.player_turn is not None:
        return session.player_turn
    return session.moon_swap_turn


def _take_bot_action(session: GameSession, game_id: int) -> None:
    # The player left of the dealer bids first AND leads the first trick if
    # they win (see GameSession._begin_trick_play) - only that seat can
    # guarantee WHEN a suit gets played, which is what bot.py's no-trump
    # scoring keys its risk tolerance on. Same seat, same hand throughout
    # bidding and calling trump, so this is valid at both points.
    is_first_bidder = game_id == bid_order(session.state.dealer_id)[0]
    hand = session.state.hands[game_id]

    if session.phase is Phase.CALLING_TRUMP:
        assert session.state.winning_bid is not None
        trump = choose_trump(hand, is_first_bidder)
        swap_out_card = None
        if session.state.winning_bid.rung is BidRung.MOON:
            swap_out_card = choose_moon_swap_card(hand, trump, role="bidder")
        session.call_trump(game_id, trump, swap_out_card)
    elif session.bidder_turn == game_id:
        session.submit_bid(game_id, choose_bid(hand, session.legal_bids, is_first_bidder))
    elif session.player_turn == game_id:
        assert session.state.trump is not None
        card = choose_card_to_play(hand, session.legal_plays, session.state.current_trick, session.state.trump)
        session.play_card(game_id, card)
    elif session.moon_swap_turn == game_id:
        assert session.state.trump is not None
        card = choose_moon_swap_card(hand, session.state.trump, role="partner")
        session.submit_moon_swap_card(game_id, card)


async def resolve_bot_turns(room: Room) -> None:
    """Runs any consecutive bot turns (a run of bots in a row, or bots
    spanning a hand boundary into the next hand's bidding) one at a time,
    each after its own "thinking" delay, broadcasting the result of each
    individually rather than the whole cascade at once - a no-op unless the
    game has actually started and it's currently a bot's turn.
    """
    if room.status is not RoomStatus.IN_GAME:
        return
    session = room.session
    assert session is not None

    consecutive_bids = 0
    while True:
        game_id = _current_turn_game_id(session)
        if game_id is None:
            return
        lobby_id = room.game_to_lobby.get(game_id)
        if lobby_id is None or lobby_id not in room.bot_ids:
            return

        if session.phase is Phase.BIDDING:
            delay = random.uniform(*BID_DELAY_RANGE) + consecutive_bids * BID_DELAY_INCREMENT
            consecutive_bids += 1
        elif session.phase is Phase.PLAYING:
            delay = CARD_PLAY_DELAY
            # Leading a brand new trick (current_trick is empty) after at
            # least one trick has already finished this hand - wait for the
            # previous trick to actually clear from the table before this
            # bot's own "thinking" timer even starts.
            if not session.state.current_trick and session.state.tricks:
                delay += TRICK_CLEAR_DELAY
        else:
            delay = random.uniform(*ACTION_DELAY_RANGE)
        await asyncio.sleep(delay)

        _take_bot_action(session, game_id)
        await broadcast_room(room)


async def broadcast_room(room: Room) -> None:
    if room.status is RoomStatus.LOBBY:
        await room.connections.broadcast(lambda lobby_id: build_lobby_view(room, lobby_id))
        return

    session = room.session
    assert session is not None
    bots_in_game_ids = {room.lobby_to_game[lobby_id] for lobby_id in room.bot_ids}
    await room.connections.broadcast(
        lambda lobby_id: build_state_view(
            session,
            room.lobby_to_game[lobby_id],
            room.teams,
            bots_in_game_ids,
            lobby_id == room.host_id,
        )
    )


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str) -> None:
    await websocket.accept()

    room = registry.get(room_code)
    if room is None:
        await websocket.send_json({"type": "error", "message": "room not found"})
        await websocket.close()
        return

    try:
        player_id = room.assign_seat(websocket)
    except GameFullError:
        message = (
            "game already in progress" if room.status is RoomStatus.IN_GAME else "all 4 seats are taken"
        )
        await websocket.send_json({"type": "error", "message": message})
        await websocket.close()
        return

    if room.status is RoomStatus.LOBBY:
        room.auto_balance_new_player(player_id)

    await websocket.send_json({"type": "assigned_seat", "player_id": player_id})
    await broadcast_room(room)

    try:
        while True:
            message = await websocket.receive_json()
            try:
                if room.status is RoomStatus.LOBBY:
                    handle_lobby_message(room, player_id, message)
                elif message.get("type") == "restart_game":
                    room.restart_game(player_id)
                else:
                    session = room.session
                    assert session is not None
                    handle_message(session, room.lobby_to_game[player_id], message)
            except (ValueError, KeyError) as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue
            await broadcast_room(room)  # the human's own action, shown immediately
            await resolve_bot_turns(room)  # bots then trickle in with their own delays
    except WebSocketDisconnect:
        room.connections.disconnect(player_id)
        if room.status is RoomStatus.LOBBY:
            room.forget_player(player_id)
        # Deliberately never delete a room just because it's momentarily
        # empty: an IN_GAME room needs to survive everyone briefly dropping
        # (that's the whole point of the seat-rejoin path), and even a
        # LOBBY room can go through a real but instantaneous zero-connection
        # blip - e.g. React StrictMode's dev-mode double-effect closes and
        # reopens a WebSocket right after creating a room, which raced this
        # exact cleanup into deleting the room before the real connection
        # landed. Abandoned rooms sitting in memory forever is an accepted
        # cost at this app's scale (see CLAUDE.md's hosting notes).
        if not room.connections.is_empty():
            await broadcast_room(room)
