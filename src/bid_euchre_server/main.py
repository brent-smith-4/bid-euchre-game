"""FastAPI app serving many concurrent room-code based games over WebSockets.

Each Room is fully isolated (its own ConnectionManager, its own GameSession
once started) - main.py's only job is translating WebSocket JSON messages
into Room/GameSession calls and broadcasting the result. All game-state
mutation still goes through GameSession (the sole source of truth for an
in-progress hand); Room is the sole source of truth for lobby state
(teams/colors/names/host) and for which room a given connection belongs to.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from bid_euchre.models import BidRung
from bid_euchre_server.connection_manager import GameFullError
from bid_euchre_server.protocol import build_lobby_view, build_state_view, card_from_json, trump_call_from_json
from bid_euchre_server.rate_limit import RateLimiter
from bid_euchre_server.room import Room, RoomRegistry, RoomStatus
from bid_euchre_server.session import GameSession

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
        active_session.call_trump(player_id, trump_call_from_json(message))
    elif msg_type == "play_card":
        active_session.play_card(player_id, card_from_json(message["card"]))
    elif msg_type == "swap_moon_card":
        active_session.swap_moon_card(
            player_id,
            card_from_json(message["card_from_bidder"]),
            card_from_json(message["card_from_partner"]),
        )
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
    else:
        raise ValueError(f"unknown message type: {msg_type!r}")


async def broadcast_room(room: Room) -> None:
    if room.status is RoomStatus.LOBBY:
        await room.connections.broadcast(lambda lobby_id: build_lobby_view(room, lobby_id))
        return

    session = room.session
    assert session is not None
    await room.connections.broadcast(
        lambda lobby_id: build_state_view(session, room.lobby_to_game[lobby_id], room.teams)
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
        player_id = room.connections.assign_seat(websocket)
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
                else:
                    session = room.session
                    assert session is not None
                    handle_message(session, room.lobby_to_game[player_id], message)
            except (ValueError, KeyError) as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue
            await broadcast_room(room)
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
