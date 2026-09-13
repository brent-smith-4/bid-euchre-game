"""Core data model for Bid Euchre, per CLAUDE.md's agreed shape.

Player seating is fixed: 4 players, seats 0-3, partners sit across the table
from each other (0 & 2 are partners, 1 & 3 are partners). Team id is
``player_id % 2``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Suit(Enum):
    CLUBS = "clubs"
    DIAMONDS = "diamonds"
    HEARTS = "hearts"
    SPADES = "spades"


class Rank(IntEnum):
    """Ordered low to high for the no-trump 'high' ranking (Ace high)."""

    NINE = 0
    TEN = 1
    JACK = 2
    QUEEN = 3
    KING = 4
    ACE = 5


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank


class BidRung(IntEnum):
    """The bid ladder, low to high. Values for THREE..SIX equal the number
    bid, so `.value` can be used directly as the trick-count target and for
    stuck-dealer / set-penalty arithmetic. MOON and ALONE sit above SIX.
    """

    PASS = 0
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    MOON = 7
    ALONE = 8


@dataclass(frozen=True)
class Bid:
    player_id: int
    rung: BidRung


class TrumpMode(Enum):
    SUIT = "suit"
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True)
class TrumpCall:
    mode: TrumpMode
    suit: Suit | None = None

    def __post_init__(self) -> None:
        if self.mode is TrumpMode.SUIT and self.suit is None:
            raise ValueError("TrumpCall with mode SUIT must specify a suit")
        if self.mode is not TrumpMode.SUIT and self.suit is not None:
            raise ValueError("TrumpCall with mode HIGH/LOW must not specify a suit")


@dataclass(frozen=True)
class TrickPlay:
    player_id: int
    card: Card


# Order matters: the first TrickPlay in a Trick sets the lead suit.
Trick = list[TrickPlay]

# Order doesn't carry meaning for a player's held cards.
Hand = list[Card]

NUM_PLAYERS = 4
TEAM_A = 0
TEAM_B = 1


def team_of(player_id: int) -> int:
    """Fixed partnerships: seats 0 & 2 are one team, 1 & 3 are the other."""
    return player_id % 2


def partner_of(player_id: int) -> int:
    return (player_id + 2) % NUM_PLAYERS


@dataclass
class HandState:
    dealer_id: int
    hands: dict[int, Hand]
    bid_history: list[Bid] = field(default_factory=list)
    winning_bid: Bid | None = None
    trump: TrumpCall | None = None
    tricks: list[Trick] = field(default_factory=list)
    current_trick: Trick = field(default_factory=list)
    scores: dict[int, int] = field(default_factory=lambda: {TEAM_A: 0, TEAM_B: 0})
