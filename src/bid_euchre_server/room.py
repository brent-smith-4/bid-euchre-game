"""A Room is one isolated 4-player match: a lobby (team selection, colors,
names, host controls) that turns into a GameSession once the host starts it.
RoomRegistry holds every currently-active Room, keyed by its shareable code.

Room replaces what used to be main.py's single module-level `session` +
`manager` globals - now there can be many, one per room, each with its own
ConnectionManager instance.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import Enum, auto

from fastapi import WebSocket

from bid_euchre.models import NUM_PLAYERS
from bid_euchre_server.connection_manager import ConnectionManager, GameFullError
from bid_euchre_server.session import GameSession

_CODE_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0/O, 1/I/L - unambiguous by eye
_CODE_LENGTH = 6

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

TEAM_A = 0
TEAM_B = 1
_DEFAULT_COLORS = {TEAM_A: "#3366cc", TEAM_B: "#cc3333"}


class RoomStatus(Enum):
    LOBBY = auto()
    IN_GAME = auto()


@dataclass
class TeamMeta:
    color: str
    name: str | None = None


class Room:
    def __init__(self, code: str) -> None:
        self.code = code
        self.status = RoomStatus.LOBBY
        self.connections = ConnectionManager()
        self.teams: dict[int, TeamMeta] = {
            TEAM_A: TeamMeta(color=_DEFAULT_COLORS[TEAM_A]),
            TEAM_B: TeamMeta(color=_DEFAULT_COLORS[TEAM_B]),
        }
        self.player_team: dict[int, int] = {}
        self.target_score = 52
        self.session: GameSession | None = None
        # Fixed once start_game() runs: lobby seat (connection order) -> the
        # GameSession player_id that seat actually plays as, and its reverse
        # (used to check whether the CURRENT game turn belongs to a bot).
        self.lobby_to_game: dict[int, int] = {}
        self.game_to_lobby: dict[int, int] = {}
        # Lobby seats occupied by a bot instead of a live WebSocket - never
        # appear in `self.connections`, so they don't count as "connected"
        # for host_id/rejoin purposes, but DO count as occupied seats for
        # seat-assignment and team balance, same as a human.
        self.bot_ids: set[int] = set()

    # -- read-only views ---------------------------------------------------

    @property
    def host_id(self) -> int | None:
        connected = self.connections.connected_player_ids()
        return min(connected) if connected else None

    def naming_rights_holder(self, team: int) -> int | None:
        members = [p for p, t in self.player_team.items() if t == team and p not in self.bot_ids]
        return min(members) if members else None

    # -- joining -------------------------------------------------------------

    def assign_seat(self, websocket: WebSocket) -> int:
        """Give a new WebSocket connection the lowest lobby seat not already
        occupied by either a live connection or a bot.
        """
        occupied = set(self.connections.connected_player_ids()) | self.bot_ids
        for player_id in range(NUM_PLAYERS):
            if player_id not in occupied:
                self.connections.occupy(player_id, websocket)
                return player_id
        raise GameFullError("all 4 seats are taken")

    def auto_balance_new_player(self, player_id: int) -> None:
        team_a_count = sum(1 for t in self.player_team.values() if t == TEAM_A)
        team_b_count = sum(1 for t in self.player_team.values() if t == TEAM_B)
        self.player_team[player_id] = TEAM_A if team_a_count <= team_b_count else TEAM_B

    def forget_player(self, player_id: int) -> None:
        self.player_team.pop(player_id, None)

    def add_bot(self, requester_id: int) -> int:
        self._require_lobby()
        if requester_id != self.host_id:
            raise ValueError("only the host may add a bot")

        occupied = set(self.connections.connected_player_ids()) | self.bot_ids
        for player_id in range(NUM_PLAYERS):
            if player_id not in occupied:
                self.bot_ids.add(player_id)
                self.auto_balance_new_player(player_id)
                return player_id
        raise ValueError("room is full")

    def remove_bot(self, requester_id: int, bot_id: int) -> None:
        self._require_lobby()
        if requester_id != self.host_id:
            raise ValueError("only the host may remove a bot")
        if bot_id not in self.bot_ids:
            raise ValueError("that seat isn't a bot")
        self.bot_ids.discard(bot_id)
        self.forget_player(bot_id)

    # -- lobby actions -------------------------------------------------------

    def _require_lobby(self) -> None:
        if self.status is not RoomStatus.LOBBY:
            raise ValueError("not in the lobby phase")

    def swap_team(self, player_id: int, with_player_id: int) -> None:
        self._require_lobby()
        if player_id not in self.player_team or with_player_id not in self.player_team:
            raise ValueError("both players must be seated in this room")
        if self.player_team[player_id] == self.player_team[with_player_id]:
            raise ValueError("already on the same team")
        self.player_team[player_id], self.player_team[with_player_id] = (
            self.player_team[with_player_id],
            self.player_team[player_id],
        )

    def set_team_color(self, player_id: int, team: int, color: str) -> None:
        self._require_lobby()
        if team not in self.teams:
            raise ValueError("invalid team")
        if self.player_team.get(player_id) != team:
            raise ValueError("only players on that team may change its color")
        if not _HEX_COLOR.match(color):
            raise ValueError("color must be a hex string like #3366cc")
        self.teams[team].color = color

    def set_team_name(self, player_id: int, team: int, name: str) -> None:
        self._require_lobby()
        if team not in self.teams:
            raise ValueError("invalid team")
        if player_id != self.naming_rights_holder(team):
            raise ValueError("only that team's first player may set its name")
        name = name.strip()
        self.teams[team].name = name or None

    def set_target_score(self, player_id: int, value: int) -> None:
        self._require_lobby()
        if player_id != self.host_id:
            raise ValueError("only the host may set the target score")
        if value <= 0:
            raise ValueError("target score must be positive")
        self.target_score = value

    def start_game(self, player_id: int) -> None:
        self._require_lobby()
        if player_id != self.host_id:
            raise ValueError("only the host may start the game")

        team_a = sorted(p for p, t in self.player_team.items() if t == TEAM_A)
        team_b = sorted(p for p, t in self.player_team.items() if t == TEAM_B)
        if len(team_a) != 2 or len(team_b) != 2:
            raise ValueError("both teams need exactly 2 players to start")

        # team_of() in models.py is player_id % 2, so team A -> seats {0, 2},
        # team B -> seats {1, 3}.
        self.lobby_to_game = {
            team_a[0]: 0,
            team_a[1]: 2,
            team_b[0]: 1,
            team_b[1]: 3,
        }
        self.game_to_lobby = {game_id: lobby_id for lobby_id, game_id in self.lobby_to_game.items()}
        self.session = GameSession(target_score=self.target_score, first_dealer_id=0)
        self.status = RoomStatus.IN_GAME


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self) -> Room:
        while True:
            code = "".join(secrets.choice(_CODE_CHARSET) for _ in range(_CODE_LENGTH))
            if code not in self._rooms:
                room = Room(code)
                self._rooms[code] = room
                return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code)

    def remove(self, code: str) -> None:
        self._rooms.pop(code, None)
