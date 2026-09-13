"""Tracks which WebSocket connection occupies which of the 4 seats in a
single room, and broadcasts personalized views to everyone connected.

Deliberately generic over *what* gets broadcast (a lobby view, a game view,
...) - callers pass a per-viewer builder function, so this module has no
knowledge of GameSession/Room at all.
"""

from __future__ import annotations

from typing import Callable

from fastapi import WebSocket

from bid_euchre.models import NUM_PLAYERS


class GameFullError(RuntimeError):
    pass


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, WebSocket] = {}

    def assign_seat(self, websocket: WebSocket) -> int:
        for player_id in range(NUM_PLAYERS):
            if player_id not in self._connections:
                self._connections[player_id] = websocket
                return player_id
        raise GameFullError("all 4 seats are taken")

    def disconnect(self, player_id: int) -> None:
        self._connections.pop(player_id, None)

    def connected_player_ids(self) -> list[int]:
        return list(self._connections)

    def is_empty(self) -> bool:
        return not self._connections

    async def send_personal(self, player_id: int, message: dict[str, object]) -> None:
        websocket = self._connections.get(player_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(message)
        except Exception:
            # That connection is already gone (it can race ahead of the
            # WebSocketDisconnect handler that would normally clean it up) -
            # never let one dead recipient break delivery to everyone else
            # in a broadcast.
            self.disconnect(player_id)

    async def broadcast(self, build_view: Callable[[int], dict[str, object]]) -> None:
        for player_id in self.connected_player_ids():
            await self.send_personal(player_id, build_view(player_id))
