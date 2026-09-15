// Mirrors src/bid_euchre/models.py and src/bid_euchre_server/protocol.py's
// wire shapes exactly. The server is the sole source of truth for game
// state and legality — this file only types the wire and formats it for
// display; it must never grow its own bid/follow-suit rules.

export type Suit = "CLUBS" | "DIAMONDS" | "HEARTS" | "SPADES";
export type Rank = "NINE" | "TEN" | "JACK" | "QUEEN" | "KING" | "ACE";

// Ordered low to high, matching BidRung in models.py.
export const BID_LADDER = ["PASS", "THREE", "FOUR", "FIVE", "SIX", "MOON", "ALONE"] as const;
export type BidRung = (typeof BID_LADDER)[number];

export type TrumpMode = "SUIT" | "HIGH" | "LOW";

export interface Card {
  suit: Suit;
  rank: Rank;
}

export interface Bid {
  player_id: number;
  rung: BidRung;
}

export interface TrumpCall {
  mode: TrumpMode;
  suit: Suit | null;
}

export interface TrickPlay {
  player_id: number;
  card: Card;
}

export type Phase = "BIDDING" | "CALLING_TRUMP" | "MOON_SWAP" | "PLAYING" | "GAME_OVER";

export interface TeamMeta {
  color: string;
  name: string | null;
}

export interface LobbyTeamMeta extends TeamMeta {
  naming_rights_holder: number | null;
}

// The payload build_state_view sends, personalized per viewer.
export interface StateView {
  type: "state";
  phase: Phase;
  your_player_id: number;
  dealer_id: number;
  your_hand: Card[];
  hand_sizes: Record<number, number>;
  bid_history: Bid[];
  winning_bid: Bid | null;
  trump: TrumpCall | null;
  tricks_completed: number;
  tricks_won: Record<number, number>;
  last_trick_winner: number | null;
  last_trick: TrickPlay[] | null;
  current_trick: TrickPlay[];
  scores: Record<number, number>;
  target_score: number;
  bidder_turn: number | null;
  player_turn: number | null;
  moon_swap_turn: number | null;
  legal_bids: BidRung[];
  legal_plays: Card[];
  teams: Record<number, TeamMeta>;
  bots: number[];
  is_host: boolean;
}

// The payload build_lobby_view sends, personalized per viewer, while a
// room's game hasn't started yet.
export interface LobbyState {
  type: "lobby_state";
  room_code: string;
  your_player_id: number;
  host_id: number | null;
  target_score: number;
  players: Record<number, number>; // player_id -> team (0/1)
  teams: Record<number, LobbyTeamMeta>;
  bots: number[];
}

export interface AssignedSeatMessage {
  type: "assigned_seat";
  player_id: number;
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type ServerMessage = StateView | LobbyState | AssignedSeatMessage | ErrorMessage;

export type ClientMessage =
  | { type: "bid"; rung: BidRung }
  | { type: "call_trump"; mode: TrumpMode; suit: Suit | null; swap_out_card: Card | null }
  | { type: "submit_moon_swap_card"; card: Card }
  | { type: "play_card"; card: Card }
  | { type: "swap_team"; with_player_id: number }
  | { type: "set_team_color"; team: number; color: string }
  | { type: "set_team_name"; team: number; name: string }
  | { type: "set_target_score"; value: number }
  | { type: "start_game" }
  | { type: "add_bot" }
  | { type: "remove_bot"; bot_id: number }
  | { type: "restart_game" };

// -- display helpers ---------------------------------------------------

const SUIT_SYMBOL: Record<Suit, string> = {
  CLUBS: "♣",
  DIAMONDS: "♦",
  HEARTS: "♥",
  SPADES: "♠",
};

const RED_SUITS = new Set<Suit>(["DIAMONDS", "HEARTS"]);

const RANK_LABEL: Record<Rank, string> = {
  NINE: "9",
  TEN: "10",
  JACK: "J",
  QUEEN: "Q",
  KING: "K",
  ACE: "A",
};

const BID_LABEL: Record<BidRung, string> = {
  PASS: "Pass",
  THREE: "3",
  FOUR: "4",
  FIVE: "5",
  SIX: "6",
  MOON: "Shoot the Moon",
  ALONE: "Go Alone",
};

// Display-only call signs for seats 0-3. Purely cosmetic: the wire protocol
// and every rules/turn-order check still identify players by their
// player_id (int) - this never becomes a lookup key anywhere else.
const PLAYER_NAME = ["Alpha", "Bravo", "Charlie", "Delta"];

export function playerName(playerId: number): string {
  return PLAYER_NAME[playerId] ?? `Player ${playerId}`;
}

// Fixed partnerships: seats 0 & 2 are one team, 1 & 3 are the other -
// mirrors bid_euchre.models.team_of exactly (a static seat-parity rule, not
// game state, so computing it client-side isn't the server-authority
// violation CLAUDE.md warns against for turn/legality logic).
export function teamOf(playerId: number): number {
  return playerId % 2;
}

export function partnerOf(playerId: number): number {
  return (playerId + 2) % 4;
}

export function playerColor(teams: Record<number, TeamMeta>, playerId: number): string {
  return teams[teamOf(playerId)].color;
}

export function teamLabel(teams: Record<number, TeamMeta>, teamId: number): string {
  return teams[teamId]?.name ?? (teamId === 0 ? "Team A" : "Team B");
}

export function suitSymbol(suit: Suit): string {
  return SUIT_SYMBOL[suit];
}

export function suitColor(suit: Suit): "red" | "black" {
  return RED_SUITS.has(suit) ? "red" : "black";
}

export function rankLabel(rank: Rank): string {
  return RANK_LABEL[rank];
}

export function bidLabel(rung: BidRung): string {
  return BID_LABEL[rung];
}

// Per-rung explanation for the bidding UI - CLAUDE.md's Game rules section
// is the source of truth for these numbers (scoring, moon/alone payouts).
const BID_DESCRIPTION: Record<BidRung, string> = {
  PASS: "Sit this bidding round out.",
  THREE: "Commit to winning at least 3 of the 6 tricks with your partner.",
  FOUR: "Commit to winning at least 4 of the 6 tricks with your partner.",
  FIVE: "Commit to winning at least 5 of the 6 tricks with your partner.",
  SIX: "Commit to winning all 6 tricks with your partner.",
  MOON: "Shoot the Moon: commit to winning all 6 tricks by yourself - your partner sits out this " +
    "hand, but swaps one hidden card with you first after you call trump. Worth 12 points if " +
    "made, -12 if set.",
  ALONE: "Go Alone: commit to winning all 6 tricks by yourself - your partner sits out this hand, " +
    "with no card swap first. Worth 24 points if made, -24 if set.",
};

export function bidDescription(rung: BidRung): string {
  return BID_DESCRIPTION[rung];
}

export function cardLabel(card: Card): string {
  return `${rankLabel(card.rank)}${suitSymbol(card.suit)}`;
}

export function cardKey(card: Card): string {
  return `${card.suit}-${card.rank}`;
}

export function cardsEqual(a: Card, b: Card): boolean {
  return a.suit === b.suit && a.rank === b.rank;
}

// Maps a raw server error string (the message on IllegalPlayError/ValueError
// exceptions - see IllegalPlayError in src/bid_euchre/trick.py, and the
// ValueErrors raised throughout src/bid_euchre_server/session.py) to
// player-facing copy. Per the "illegal-action-messaging" decision, this is
// deliberately specific rather than one generic "illegal move" toast.
const ERROR_COPY: Record<string, string> = {
  "must follow suit": "You must follow suit!",
  "card not in hand": "You don't have that card.",
};

const TURN_ERROR_PATTERNS: RegExp[] = [/not player \d+'s turn to bid/, /not player \d+'s turn to play/];

export function describeError(raw: string): string {
  const mapped = ERROR_COPY[raw];
  if (mapped) return mapped;
  if (TURN_ERROR_PATTERNS.some((pattern) => pattern.test(raw))) {
    return "It's not your turn yet.";
  }
  if (raw.startsWith("illegal bid")) {
    return "That bid isn't legal right now.";
  }
  return raw || "Something went wrong.";
}
