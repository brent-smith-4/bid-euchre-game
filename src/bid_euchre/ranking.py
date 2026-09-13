"""Card ranking: the single source of truth for "which card beats which,"
covering all three trump modes (suit w/ bowers, no-trump high, no-trump low).
"""

from __future__ import annotations

from .models import Card, Rank, Suit, TrumpCall, TrumpMode

_SAME_COLOR: dict[Suit, Suit] = {
    Suit.CLUBS: Suit.SPADES,
    Suit.SPADES: Suit.CLUBS,
    Suit.DIAMONDS: Suit.HEARTS,
    Suit.HEARTS: Suit.DIAMONDS,
}

_RIGHT_BOWER = 1000
_LEFT_BOWER = 999
_TRUMP_BASE = 900


def is_right_bower(card: Card, trump_suit: Suit) -> bool:
    return card.rank is Rank.JACK and card.suit is trump_suit


def is_left_bower(card: Card, trump_suit: Suit) -> bool:
    return card.rank is Rank.JACK and card.suit is _SAME_COLOR[trump_suit]


def effective_suit(card: Card, trump: TrumpCall) -> Suit:
    """The suit `card` counts as for follow-suit purposes. The left bower
    counts as trump, per CLAUDE.md, regardless of its printed suit.
    """
    if trump.mode is TrumpMode.SUIT:
        assert trump.suit is not None
        if is_left_bower(card, trump.suit):
            return trump.suit
    return card.suit


def is_trump(card: Card, trump: TrumpCall) -> bool:
    return trump.mode is TrumpMode.SUIT and effective_suit(card, trump) == trump.suit


def card_rank_value(card: Card, trump: TrumpCall) -> int:
    """A total ordering over all cards for the given trump call. Comparable
    across any two cards directly (via `sorted()`/`max()`) — higher wins.

    Note this does NOT account for follow-suit: a card that failed to follow
    the lead suit and isn't trump can still get a rank value here, it's up to
    trick-winner logic to exclude it from contention first.
    """
    if trump.mode is TrumpMode.SUIT:
        assert trump.suit is not None
        if is_right_bower(card, trump.suit):
            return _RIGHT_BOWER
        if is_left_bower(card, trump.suit):
            return _LEFT_BOWER
        if card.suit is trump.suit:
            return _TRUMP_BASE + card.rank.value
        return card.rank.value

    if trump.mode is TrumpMode.HIGH:
        return card.rank.value

    # LOW: 9 ranks highest, Ace lowest — invert the natural rank scale.
    return Rank.ACE.value - card.rank.value
