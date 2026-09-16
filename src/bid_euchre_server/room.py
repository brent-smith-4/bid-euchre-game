"""A Room is one isolated 4-player match: a lobby (team selection, colors,
names, host controls) that turns into a GameSession once the host starts it.
RoomRegistry holds every currently-active Room, keyed by its shareable code.

Room replaces what used to be main.py's single module-level `session` +
`manager` globals - now there can be many, one per room, each with its own
ConnectionManager instance.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import Enum, auto

from fastapi import WebSocket

from bid_euchre.models import NUM_PLAYERS
from bid_euchre_server.connection_manager import ConnectionManager, GameFullError
from bid_euchre_server.session import GameSession, Phase

_CODE_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # excludes 0/O, 1/I/L - unambiguous by eye
_CODE_LENGTH = 6

TEAM_A = 0
TEAM_B = 1

# The only colors a team may pick: bright variants of the 3 primary + 3
# secondary colors, offered to players as a fixed dropdown rather than a
# free-form color picker (see Lobby.tsx) - validated again here so a
# tampered client can't smuggle in an arbitrary color.
TEAM_COLORS = {
    "#ff3b30": "Red",
    "#ff9500": "Orange",
    "#ffcc00": "Yellow",
    "#34c759": "Green",
    "#0a84ff": "Blue",
    "#af52de": "Purple",
}
_DEFAULT_COLORS = {TEAM_A: "#0a84ff", TEAM_B: "#ff3b30"}

_MAX_PLAYER_NAME_LENGTH = 20


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
        # Custom display names, keyed by lobby id (the stable identity for a
        # connection - see lobby_to_game) so a player's chosen name follows
        # them from the lobby into the game regardless of which fixed-seat
        # game id they end up assigned to. Absent entries fall back to the
        # cosmetic Alpha/Bravo/Charlie/Delta labels (see protocol.ts).
        self.player_names: dict[int, str] = {}
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
        self.player_names.pop(player_id, None)

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
        if color not in TEAM_COLORS:
            raise ValueError("color must be one of the offered swatches")
        self.teams[team].color = color

    def set_team_name(self, player_id: int, team: int, name: str) -> None:
        self._require_lobby()
        if team not in self.teams:
            raise ValueError("invalid team")
        if player_id != self.naming_rights_holder(team):
            raise ValueError("only that team's first player may set its name")
        name = name.strip()
        self.teams[team].name = name or None

    def set_player_name(self, player_id: int, name: str) -> None:
        self._require_lobby()
        name = name.strip()[:_MAX_PLAYER_NAME_LENGTH]
        if name:
            self.player_names[player_id] = name
        else:
            self.player_names.pop(player_id, None)

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

    def restart_game(self, player_id: int) -> None:
        """Start a brand new match in this same room - same seats, teams,
        colors, and bots as the match that just ended, scores back to 0.
        Only legal once the previous match has actually finished, so a
        restart never discards a game still in progress.
        """
        if self.status is not RoomStatus.IN_GAME or self.session is None:
            raise ValueError("not in a game")
        if self.session.phase is not Phase.GAME_OVER:
            raise ValueError("game is not over yet")
        if player_id != self.host_id:
            raise ValueError("only the host may restart the game")

        self.session = GameSession(target_score=self.target_score, first_dealer_id=0)


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
