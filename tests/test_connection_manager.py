"""Unit tests for ConnectionManager, in particular that one dead/failing
connection during a broadcast can't block delivery to everyone else - this
matters because a client can race ahead of the server's own disconnect
handling (see the room-lobby StrictMode race this was written to guard
against).
"""

import asyncio

from bid_euchre_server.connection_manager import ConnectionManager


class _WorkingWebSocket:
    def __init__(self) -> None:
        self.received: list[dict[str, object]] = []

    async def send_json(self, message: dict[str, object]) -> None:
        self.received.append(message)


class _DeadWebSocket:
    async def send_json(self, message: dict[str, object]) -> None:
        raise RuntimeError("Cannot call \"send\" once a close message has been sent.")


def test_broadcast_skips_a_dead_connection_without_blocking_the_rest() -> None:
    manager = ConnectionManager()
    dead = _DeadWebSocket()
    alive = _WorkingWebSocket()
    manager._connections[0] = dead  # type: ignore[assignment]  # noqa: SLF001
    manager._connections[1] = alive  # type: ignore[assignment]  # noqa: SLF001

    asyncio.run(manager.broadcast(lambda player_id: {"type": "state", "player_id": player_id}))

    assert alive.received == [{"type": "state", "player_id": 1}]


def test_a_failed_send_self_heals_by_disconnecting_that_seat() -> None:
    manager = ConnectionManager()
    manager._connections[0] = _DeadWebSocket()  # type: ignore[assignment]  # noqa: SLF001

    asyncio.run(manager.send_personal(0, {"type": "state"}))

    assert manager.connected_player_ids() == []
