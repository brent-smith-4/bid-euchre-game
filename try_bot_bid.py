"""Scratch tool for manually testing the bot bidding heuristic. Edit HAND and
IS_FIRST below, then run: python try_bot_bid.py

Card shorthand: rank + suit, e.g. "9S" = nine of spades, "TC" = ten of clubs,
"JD" = jack of diamonds, "QH" = queen of hearts, "KC" = king of clubs,
"AS" = ace of spades. Ranks: 9 T J Q K A. Suits: S H D C.
"""

from bid_euchre.models import BidRung, Card, Rank, Suit
from bid_euchre_server.bot import best_bid_option, choose_bid, choose_trump

_RANKS = {"9": Rank.NINE, "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING, "A": Rank.ACE}
_SUITS = {"S": Suit.SPADES, "H": Suit.HEARTS, "D": Suit.DIAMONDS, "C": Suit.CLUBS}


def card(shorthand: str) -> Card:
    return Card(suit=_SUITS[shorthand[1].upper()], rank=_RANKS[shorthand[0].upper()])


def hand(shorthand: str) -> list[Card]:
    return [card(c) for c in shorthand.split()]


# ---- Edit these two lines ----
HAND = hand("JS KS 9S AH QD TC")
IS_FIRST = True
# -------------------------------

if __name__ == "__main__":
    legal_bids = list(BidRung)  # assume an unforced turn (PASS + everything is legal)
    option = best_bid_option(HAND, IS_FIRST)
    bid = choose_bid(HAND, legal_bids, IS_FIRST)
    trump = choose_trump(HAND, IS_FIRST)

    print(f"Hand: {' '.join(f'{c.rank.name}-{c.suit.name}' for c in HAND)}")
    print(f"Position: {'first to bid' if IS_FIRST else 'not first'}")
    print(f"Best option: {option.trump.mode.name} {option.trump.suit.name if option.trump.suit else ''}")
    print(f"Trick estimate: {option.tricks}  (unlocks moon: {option.unlocks_moon}, alone: {option.unlocks_alone})")
    print(f"-> choose_bid:   {bid.name}")
    print(f"-> choose_trump: {trump.mode.name} {trump.suit.name if trump.suit else ''}")
