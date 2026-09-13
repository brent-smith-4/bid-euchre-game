"""Integration tests for the WebSocket/HTTP wiring itself (room creation,
seating, message parsing, broadcasting, error handling) - the underlying
game rules are covered by test_session.py/bid_euchre unit tests, and lobby
business logic (team balance, swap, naming rights, host controls) is
covered by test_room.py.
"""

from typing import Any

from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

import bid_euchre_server.main as main_module
from bid_euchre_server.protocol import card_to_json
from bid_euchre_server.rate_limit import RateLimiter
from bid_euchre_server.room import RoomRegistry

import pytest


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    main_module.registry = RoomRegistry()
    main_module.room_creation_limiter = RateLimiter(max_calls=5, window_seconds=60)


def _drain(ws: WebSocketTestSession, count: int) -> list[dict[str, Any]]:
    return [ws.receive_json() for _ in range(count)]


def _drain_all(sockets: list[WebSocketTestSession], count_each: int) -> list[dict[str, Any]]:
    """Drain `count_each` messages from every socket, returning each socket's
    last message (the final broadcast, if `count_each` covers exactly one
    broadcast round).
    """
    return [_drain(ws, count_each)[-1] for ws in sockets]


def _create_room(client: TestClient) -> str:
    response = client.post("/rooms")
    assert response.status_code == 200
    return response.json()["room_code"]


def _join_and_start_game(client: TestClient, room_code: str, sockets: list[WebSocketTestSession]) -> None:
    """Connect 4 sockets to `room_code`'s lobby, drain the lobby broadcasts,
    and have the host (player 0) start the game.
    """
    _drain(sockets[0], 1 + 4)  # assigned_seat + one lobby_state per subsequent connect
    _drain(sockets[1], 1 + 3)
    _drain(sockets[2], 1 + 2)
    _drain(sockets[3], 1 + 1)

    sockets[0].send_json({"type": "start_game"})
    _drain_all(sockets, 1)  # everyone's first "state" (game) broadcast


def test_create_room_returns_a_room_code() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    assert len(code) == 6


def test_room_creation_is_rate_limited_per_client() -> None:
    client = TestClient(main_module.app)
    main_module.room_creation_limiter = RateLimiter(max_calls=2, window_seconds=60)

    assert client.post("/rooms").status_code == 200
    assert client.post("/rooms").status_code == 200
    third = client.post("/rooms")
    assert third.status_code == 429


def test_unknown_room_code_is_rejected() -> None:
    client = TestClient(main_module.app)
    with client.websocket_connect("/ws/NOSUCH") as ws:
        assert ws.receive_json() == {"type": "error", "message": "room not found"}


def test_seats_assigned_in_connection_order_and_fifth_is_rejected() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    with (
        client.websocket_connect(f"/ws/{code}") as ws0,
        client.websocket_connect(f"/ws/{code}") as ws1,
        client.websocket_connect(f"/ws/{code}") as ws2,
        client.websocket_connect(f"/ws/{code}") as ws3,
    ):
        # ws0 sees: its own seat + one lobby broadcast per subsequent connect (3 more).
        msgs0 = _drain(ws0, 1 + 4)
        msgs1 = _drain(ws1, 1 + 3)
        msgs2 = _drain(ws2, 1 + 2)
        msgs3 = _drain(ws3, 1 + 1)

        assert msgs0[0] == {"type": "assigned_seat", "player_id": 0}
        assert msgs1[0] == {"type": "assigned_seat", "player_id": 1}
        assert msgs2[0] == {"type": "assigned_seat", "player_id": 2}
        assert msgs3[0] == {"type": "assigned_seat", "player_id": 3}

        for msgs in (msgs0, msgs1, msgs2, msgs3):
            assert all(m["type"] == "lobby_state" for m in msgs[1:])

        # 5th connection: lobby is full.
        with client.websocket_connect(f"/ws/{code}") as ws4:
            reject = ws4.receive_json()
            assert reject == {"type": "error", "message": "all 4 seats are taken"}


def test_two_rooms_do_not_interfere() -> None:
    client = TestClient(main_module.app)
    code_a = _create_room(client)
    code_b = _create_room(client)
    assert code_a != code_b

    with (
        client.websocket_connect(f"/ws/{code_a}") as a0,
        client.websocket_connect(f"/ws/{code_b}") as b0,
    ):
        assert a0.receive_json() == {"type": "assigned_seat", "player_id": 0}
        assert b0.receive_json() == {"type": "assigned_seat", "player_id": 0}

        lobby_a = a0.receive_json()
        lobby_b = b0.receive_json()
        assert lobby_a["room_code"] == code_a
        assert lobby_b["room_code"] == code_b


def test_swap_team_and_set_team_name_broadcast_to_the_lobby() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    with (
        client.websocket_connect(f"/ws/{code}") as ws0,
        client.websocket_connect(f"/ws/{code}") as ws1,
        client.websocket_connect(f"/ws/{code}") as ws2,
        client.websocket_connect(f"/ws/{code}") as ws3,
    ):
        sockets = [ws0, ws1, ws2, ws3]
        lobby0 = _drain(ws0, 1 + 4)[-1]
        _drain(ws1, 1 + 3)
        _drain(ws2, 1 + 2)
        _drain(ws3, 1 + 1)

        # players auto-balance onto teams [0, 2] / [1, 3] in join order.
        assert lobby0["players"] == {"0": 0, "1": 1, "2": 0, "3": 1}

        # naming rights for team 0 belong to player 0 (lowest id on that team).
        ws2.send_json({"type": "set_team_name", "team": 0, "name": "The Aces"})
        error = ws2.receive_json()
        assert error["type"] == "error"

        ws0.send_json({"type": "set_team_name", "team": 0, "name": "The Aces"})
        states = _drain_all(sockets, 1)
        assert states[0]["teams"]["0"]["name"] == "The Aces"

        # swap player 1 and player 2 between teams.
        ws1.send_json({"type": "swap_team", "with_player_id": 2})
        states = _drain_all(sockets, 1)
        assert states[0]["players"] == {"0": 0, "1": 0, "2": 1, "3": 1}


def test_only_host_may_start_game_and_it_transitions_to_in_game() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    with (
        client.websocket_connect(f"/ws/{code}") as ws0,
        client.websocket_connect(f"/ws/{code}") as ws1,
        client.websocket_connect(f"/ws/{code}") as ws2,
        client.websocket_connect(f"/ws/{code}") as ws3,
    ):
        sockets = [ws0, ws1, ws2, ws3]
        _drain(ws0, 1 + 4)
        _drain(ws1, 1 + 3)
        _drain(ws2, 1 + 2)
        _drain(ws3, 1 + 1)

        ws1.send_json({"type": "start_game"})
        error = ws1.receive_json()
        assert error["type"] == "error"

        ws0.send_json({"type": "start_game"})
        states = _drain_all(sockets, 1)
        assert all(s["type"] == "state" for s in states)
        assert states[0]["phase"] == "BIDDING"


def test_bidding_and_trump_call_broadcast_over_websockets() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    with (
        client.websocket_connect(f"/ws/{code}") as ws0,
        client.websocket_connect(f"/ws/{code}") as ws1,
        client.websocket_connect(f"/ws/{code}") as ws2,
        client.websocket_connect(f"/ws/{code}") as ws3,
    ):
        sockets = [ws0, ws1, ws2, ws3]
        _join_and_start_game(client, code, sockets)

        # dealer defaults to player 0 -> bid order is [1, 2, 3, 0]
        ws1.send_json({"type": "bid", "rung": "PASS"})
        states_after_p1 = _drain_all(sockets, 1)
        assert states_after_p1[0]["bid_history"] == [{"player_id": 1, "rung": "PASS"}]

        # legal_bids is populated only for the next bidder (player 2 here,
        # since bid order after dealer 0 is [1, 2, 3, 0]).
        assert states_after_p1[2]["legal_bids"] != []
        assert states_after_p1[0]["legal_bids"] == []
        assert states_after_p1[1]["legal_bids"] == []
        assert states_after_p1[3]["legal_bids"] == []

        ws2.send_json({"type": "bid", "rung": "PASS"})
        _drain_all(sockets, 1)

        ws3.send_json({"type": "bid", "rung": "PASS"})
        _drain_all(sockets, 1)

        # dealer (player 0) is now stuck: PASS should be rejected...
        ws0.send_json({"type": "bid", "rung": "PASS"})
        error = ws0.receive_json()
        assert error["type"] == "error"

        # ...but a real bid succeeds and broadcasts to everyone.
        ws0.send_json({"type": "bid", "rung": "THREE"})
        states = _drain_all(sockets, 1)
        assert states[0]["phase"] == "CALLING_TRUMP"
        assert states[0]["winning_bid"] == {"player_id": 0, "rung": "THREE"}

        # only the bid winner (player 0) may call trump
        ws1.send_json({"type": "call_trump", "mode": "HIGH"})
        error = ws1.receive_json()
        assert error["type"] == "error"

        ws0.send_json({"type": "call_trump", "mode": "HIGH"})
        states = _drain_all(sockets, 1)
        assert states[0]["phase"] == "PLAYING"
        assert states[0]["trump"] == {"mode": "HIGH", "suit": None}
        # player 0 is dealer (and, here, also the bid winner) - but the
        # player LEFT of the dealer leads the first trick regardless of who
        # won the bid, so player 1 goes first, not player 0.
        assert states[0]["player_turn"] == 1
        assert states[0]["last_trick_winner"] is None  # no trick played yet

        # legal_plays is populated only for the player whose turn it is,
        # and only lists cards actually in that player's own hand.
        assert states[1]["legal_plays"] != []
        legal_cards = states[1]["legal_plays"]
        assert all(c in states[1]["your_hand"] for c in legal_cards)
        assert states[0]["legal_plays"] == []
        assert states[2]["legal_plays"] == []
        assert states[3]["legal_plays"] == []

        # Play out the first trick (one legal card per player) and confirm
        # last_trick_winner is broadcast to everyone once it resolves.
        room = main_module.registry.get(code)
        assert room is not None and room.session is not None
        for _ in range(4):
            game_id = room.session.player_turn
            assert game_id is not None
            card = room.session.legal_plays[0]
            lobby_id = next(lid for lid, gid in room.lobby_to_game.items() if gid == game_id)
            sockets[lobby_id].send_json({"type": "play_card", "card": card_to_json(card)})
            states = _drain_all(sockets, 1)

        assert states[0]["last_trick_winner"] is not None
        assert states[0]["last_trick_winner"] == states[1]["last_trick_winner"]


def test_disconnect_during_game_frees_seat_for_rejoin() -> None:
    """Player 1 needs to disconnect mid-game while players 0, 2, 3 stay
    connected (so the room survives - an empty room gets cleaned up
    entirely). `assign_seat` hands out ids strictly in connection order, so
    plain nested `with` blocks can't express "2nd to connect, 1st to
    disconnect" - hence the manual enter/exit instead of `with`.
    """
    client = TestClient(main_module.app)
    code = _create_room(client)

    session0 = client.websocket_connect(f"/ws/{code}")
    session1 = client.websocket_connect(f"/ws/{code}")
    session2 = client.websocket_connect(f"/ws/{code}")
    session3 = client.websocket_connect(f"/ws/{code}")
    ws0, ws1, ws2, ws3 = (s.__enter__() for s in (session0, session1, session2, session3))

    try:
        _join_and_start_game(client, code, [ws0, ws1, ws2, ws3])

        session1.__exit__(None, None, None)  # player 1 disconnects mid-game

        with client.websocket_connect(f"/ws/{code}") as rejoined:
            assigned = rejoined.receive_json()
            assert assigned == {"type": "assigned_seat", "player_id": 1}
            state = rejoined.receive_json()
            assert state["type"] == "state"
            assert state["your_player_id"] == 1  # lobby seat 1 -> game seat 1
    finally:
        session0.__exit__(None, None, None)
        session2.__exit__(None, None, None)
        session3.__exit__(None, None, None)


def test_room_becomes_full_again_error_once_in_game() -> None:
    client = TestClient(main_module.app)
    code = _create_room(client)
    with (
        client.websocket_connect(f"/ws/{code}") as ws0,
        client.websocket_connect(f"/ws/{code}") as ws1,
        client.websocket_connect(f"/ws/{code}") as ws2,
        client.websocket_connect(f"/ws/{code}") as ws3,
    ):
        sockets = [ws0, ws1, ws2, ws3]
        _join_and_start_game(client, code, sockets)

        with client.websocket_connect(f"/ws/{code}") as ws4:
            reject = ws4.receive_json()
            assert reject == {"type": "error", "message": "game already in progress"}
