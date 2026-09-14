"""Unit tests for Room/RoomRegistry lobby logic - team balance/swap, color
and name rights, host-only controls, and the seat mapping start_game()
builds. WebSocket wiring itself is covered by test_main.py.
"""

from bid_euchre_server.room import RoomRegistry, RoomStatus, TEAM_A, TEAM_B

import pytest


class _FakeWebSocket:
    """Room/ConnectionManager never calls anything on the websocket during
    seat assignment - any distinct object works as a stand-in connection.
    """


def _join(room, n=1):
    """Connect `n` fresh fake players and return their assigned player_ids."""
    return [room.assign_seat(_FakeWebSocket()) for _ in range(n)]


def _join_full_room():
    registry = RoomRegistry()
    room = registry.create_room()
    ids = _join(room, 4)
    for player_id in ids:
        room.auto_balance_new_player(player_id)
    return room, ids


def test_create_room_generates_unique_unambiguous_codes() -> None:
    registry = RoomRegistry()
    codes = {registry.create_room().code for _ in range(50)}
    assert len(codes) == 50  # all unique
    for code in codes:
        assert len(code) == 6
        assert not (set(code) & set("0O1IL"))  # excluded ambiguous characters


def test_registry_get_and_remove() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    assert registry.get(room.code) is room
    registry.remove(room.code)
    assert registry.get(room.code) is None


def test_new_players_auto_balance_onto_the_smaller_team() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    ids = _join(room, 4)
    for player_id in ids:
        room.auto_balance_new_player(player_id)

    team_a = [p for p in ids if room.player_team[p] == TEAM_A]
    team_b = [p for p in ids if room.player_team[p] == TEAM_B]
    assert len(team_a) == 2
    assert len(team_b) == 2


def test_host_is_lowest_connected_player_id_and_self_heals_on_disconnect() -> None:
    room, ids = _join_full_room()
    assert room.host_id == 0

    room.connections.disconnect(0)
    assert room.host_id == 1


def test_naming_rights_holder_is_lowest_id_on_that_team() -> None:
    room, ids = _join_full_room()
    team_a_members = sorted(p for p in ids if room.player_team[p] == TEAM_A)
    assert room.naming_rights_holder(TEAM_A) == team_a_members[0]


def test_swap_team_exchanges_both_players_teams() -> None:
    room, ids = _join_full_room()
    a_player = next(p for p in ids if room.player_team[p] == TEAM_A)
    b_player = next(p for p in ids if room.player_team[p] == TEAM_B)

    room.swap_team(a_player, b_player)

    assert room.player_team[a_player] == TEAM_B
    assert room.player_team[b_player] == TEAM_A


def test_swap_team_rejects_same_team_pair() -> None:
    room, ids = _join_full_room()
    team_a_members = [p for p in ids if room.player_team[p] == TEAM_A]
    with pytest.raises(ValueError):
        room.swap_team(team_a_members[0], team_a_members[1])


def test_only_players_on_a_team_may_set_its_color() -> None:
    room, ids = _join_full_room()
    outsider = next(p for p in ids if room.player_team[p] != TEAM_A)
    with pytest.raises(ValueError):
        room.set_team_color(outsider, TEAM_A, "#123456")

    member = next(p for p in ids if room.player_team[p] == TEAM_A)
    room.set_team_color(member, TEAM_A, "#123456")
    assert room.teams[TEAM_A].color == "#123456"


def test_set_team_color_rejects_non_hex_values() -> None:
    room, ids = _join_full_room()
    member = next(p for p in ids if room.player_team[p] == TEAM_A)
    with pytest.raises(ValueError):
        room.set_team_color(member, TEAM_A, "blue")


def test_only_naming_rights_holder_may_set_team_name() -> None:
    room, ids = _join_full_room()
    team_a_members = sorted(p for p in ids if room.player_team[p] == TEAM_A)
    holder, other = team_a_members[0], team_a_members[1]

    with pytest.raises(ValueError):
        room.set_team_name(other, TEAM_A, "The Aces")

    room.set_team_name(holder, TEAM_A, "The Aces")
    assert room.teams[TEAM_A].name == "The Aces"


def test_only_host_may_set_target_score_and_start_game() -> None:
    room, ids = _join_full_room()
    non_host = next(p for p in ids if p != room.host_id)

    with pytest.raises(ValueError):
        room.set_target_score(non_host, 100)
    room.set_target_score(room.host_id, 100)
    assert room.target_score == 100

    with pytest.raises(ValueError):
        room.start_game(non_host)


def test_start_game_requires_exactly_two_players_per_team() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    ids = _join(room, 3)
    for player_id in ids:
        room.auto_balance_new_player(player_id)

    with pytest.raises(ValueError):
        room.start_game(room.host_id)


def test_start_game_maps_teams_to_fixed_partnership_seats() -> None:
    room, ids = _join_full_room()
    team_a = sorted(p for p in ids if room.player_team[p] == TEAM_A)
    team_b = sorted(p for p in ids if room.player_team[p] == TEAM_B)

    room.start_game(room.host_id)

    assert room.status is RoomStatus.IN_GAME
    assert room.session is not None
    # team_of() in models.py is player_id % 2 -> team A is seats {0, 2}, team B is {1, 3}.
    assert room.lobby_to_game[team_a[0]] == 0
    assert room.lobby_to_game[team_a[1]] == 2
    assert room.lobby_to_game[team_b[0]] == 1
    assert room.lobby_to_game[team_b[1]] == 3
    # game_to_lobby is the exact reverse of lobby_to_game.
    for lobby_id, game_id in room.lobby_to_game.items():
        assert room.game_to_lobby[game_id] == lobby_id


def test_lobby_actions_rejected_once_game_has_started() -> None:
    room, ids = _join_full_room()
    room.start_game(room.host_id)

    with pytest.raises(ValueError):
        room.swap_team(ids[0], ids[1])
    with pytest.raises(ValueError):
        room.set_target_score(room.host_id, 10)
    with pytest.raises(ValueError):
        room.start_game(room.host_id)


def test_add_bot_is_host_only_and_fills_the_lowest_open_seat() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    host = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(host)
    non_host = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(non_host)

    with pytest.raises(ValueError):
        room.add_bot(non_host)

    bot_id = room.add_bot(host)
    assert bot_id == 2  # lowest seat not already taken by a human
    assert bot_id in room.bot_ids
    assert bot_id in room.player_team  # auto-balanced onto a team like a human


def test_add_bot_does_not_collide_with_human_seats() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    human = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(human)

    bot_ids = [room.add_bot(human) for _ in range(3)]

    assert bot_ids == [1, 2, 3]
    with pytest.raises(ValueError):
        room.add_bot(human)  # room is full


def test_bots_count_toward_start_games_two_per_team_requirement() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    host = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(host)
    for _ in range(3):
        room.add_bot(host)

    room.start_game(host)

    assert room.status is RoomStatus.IN_GAME


def test_remove_bot_frees_its_seat_and_is_host_only() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    host = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(host)
    non_host = room.assign_seat(_FakeWebSocket())
    room.auto_balance_new_player(non_host)
    bot_id = room.add_bot(host)

    with pytest.raises(ValueError):
        room.remove_bot(non_host, bot_id)
    with pytest.raises(ValueError):
        room.remove_bot(host, 99)  # not a bot seat

    room.remove_bot(host, bot_id)
    assert bot_id not in room.bot_ids
    assert bot_id not in room.player_team
    # the seat is free again.
    assert room.add_bot(host) == bot_id


def test_naming_rights_holder_skips_bots_occupying_the_lowest_seat() -> None:
    registry = RoomRegistry()
    room = registry.create_room()
    host = room.assign_seat(_FakeWebSocket())  # seat 0
    room.auto_balance_new_player(host)  # team A
    bot_id = room.add_bot(host)  # seat 1, team B (smaller team)
    human_b = room.assign_seat(_FakeWebSocket())  # seat 2 -> team A (still smaller after bot)
    room.auto_balance_new_player(human_b)

    # Put a second human on team B alongside the bot, at a higher seat id,
    # so team B's lowest RAW id is the bot - naming rights must skip it.
    human_on_team_b = room.assign_seat(_FakeWebSocket())  # seat 3
    room.auto_balance_new_player(human_on_team_b)
    room.player_team[human_on_team_b] = room.player_team[bot_id]

    assert bot_id < human_on_team_b  # the bot really is the lower id
    assert room.naming_rights_holder(room.player_team[bot_id]) == human_on_team_b
