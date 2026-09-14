# Changelog

Tracks what's been built against CLAUDE.md's build order. Steps 1-4 are done.

## Step 1 — Core rules engine (`src/bid_euchre/`)

Standalone, networking-free rules engine:

- `models.py` — `Card`, `Suit`, `Rank`, `BidRung` (the ladder, PASS→ALONE), `TrumpCall`,
  `HandState`, fixed-partnership helpers (`team_of`, `partner_of`).
- `dealing.py` — deck construction, shuffling/dealing, the shoot-the-moon card swap.
- `bidding.py` — bid-order/legality checks, the stuck-dealer forced-bid rule.
- `ranking.py` — `card_rank_value`, bower logic, the single source of truth for "which card
  beats which" across all three trump modes (suit/high/low).
- `trick.py` — legal-play checks (follow-suit), trick-winner determination, ALONE's sitting-out
  partner handling.
- `scoring.py` — set/made scoring, moon (12pt) and alone (24pt) payouts.

Tested independently of everything below (`tests/test_bidding.py`, `test_dealing.py`,
`test_models.py`, `test_moon_swap.py`, `test_ranking.py`, `test_scoring.py`, `test_trick.py`).

## Step 2 — WebSocket server (`src/bid_euchre_server/`)

- `session.py` — `GameSession`, the turn-by-turn orchestrator wrapping the rules engine for one
  full match (bidding → trump call → trick play → scoring → next hand → game over).
- `protocol.py` — wire (de)serialization and the personalized `build_state_view` (each player
  only ever sees their own hand).
- `connection_manager.py` / `main.py` (original version) — a single in-memory game over one
  `/ws` endpoint, first-come seating for up to 4 connections.

## Step 3 — React frontend for one live game (`frontend/`)

Vite + React + TypeScript, chosen over Next.js — no SSR/routing was earned yet for a single
client-rendered real-time screen (revisited in step 4, see below).

- `protocol.ts` — TypeScript mirror of the wire shapes, card/bid display helpers, and
  `describeError` (maps server error strings to specific player-facing copy, e.g. "You must
  follow suit!").
- `useGameSocket.ts` — owns the WebSocket connection; every incoming state message fully
  replaces prior state (server-authoritative, no optimistic UI).
- Components: `Table`/`Seat`/`TrickArea` (table layout, rotated so the viewer is always
  "south"), `Hand` (own cards, greyed by server-provided `legal_plays`), `BiddingPanel` (ladder
  buttons gated by server-provided `legal_bids`), `TrumpCallPanel`, `ScoreBoard`,
  `GameOverScreen`.
- Server additions to support the UI without duplicating rules in JS: `GameSession.legal_bids` /
  `legal_plays` properties, threaded into `build_state_view`.
- `useRoundBanner` — diffs consecutive states to announce "You won/lost the bid!" and "Your
  team won/lost the trick!" (bid outcome is per-player, trick outcome is per-team).
- Players display as call signs (Alpha/Bravo/Charlie/Delta) instead of raw ids — cosmetic only,
  turn logic still keys off the numeric `player_id`.

**Known gap at the time, resolved in step 4 (see below):** the shoot-the-moon card swap needed a
two-phase blind-submit protocol (`session.swap_moon_card` originally expected the bidder to
already know the partner's card value, which the wire protocol never actually revealed to them).

## Step 4 — Room-code based lobbies

Replaced the single global game with many isolated, concurrent rooms.

- `room.py` (new) — `Room` (one lobby-then-match instance: `ConnectionManager`, team
  auto-balance, target score, the fixed lobby-seat→game-seat mapping computed once the host
  starts), `RoomRegistry` (in-memory, keyed by a 6-character unambiguous room code).
- `rate_limit.py` (new) — a minimal in-memory per-IP fixed-window limiter on room creation (no
  new dependency — this app runs at friends-group scale).
- `main.py` — `POST /rooms` (rate-limited) to allocate a room; `/ws/{room_code}` replaces the
  old bare `/ws`. A disconnect frees its seat rather than ending the match — the next connection
  to that room code reclaims it (no accounts yet to verify identity, so this is "trusted by
  having the code," same security model as the room code itself).
- Lobby features (from the `lobby-team-selection` / `match-win-condition` design notes): players
  freely swap between the two teams (`swap_team`, a pairwise action), each team picks a color
  (`<input type="color">` — a real color picker for free, no custom UI) and an optional name
  (rights held by whichever connected player has the lowest seat id on that team, self-healing on
  disconnect), and the host sets the target score and starts the match once both teams have
  exactly 2 players.
- Frontend: `useRoute` (a few lines of manual `pushState`/`popstate` handling — two screens don't
  justify a router library), `Landing` (create/join), `Lobby` (team panels, swap, color/name,
  host controls), `GameRoom` (renders `Lobby` or the existing game view depending on whether the
  match has started).

### Fixes found while building/testing step 4
- **First-trick leader was wrong.** CLAUDE.md specifies the player left of the dealer leads the
  first trick, not the high bidder (a deliberate departure from standard euchre) — the code had
  it backwards. Every existing test happened to have the bid winner coincide with the correct
  leader, so nothing caught it; added a test that picks a winner who is neither, to actually
  distinguish the two rules.
- **Invisible bid/trump buttons.** `index.css` declared `color-scheme: light dark` without an
  actual dark palette, so on a dark-mode OS the browser's native dark button-text color landed on
  our white buttons. Fixed by declaring `light` only and adding a defensive `button { color:
  inherit }` reset.
- **Room deleted out from under its own creator.** React StrictMode's dev-mode double-invoke of
  `useGameSocket`'s connect effect opened and immediately closed a second WebSocket on every
  mount; combined with "delete a room the instant it's empty," the phantom disconnect deleted the
  brand-new room before the real connection could use it. Fixed by removing StrictMode (its
  double-invoke doesn't mix well with an effect whose side effects are visible to other users)
  and by no longer auto-deleting rooms on empty at all — consistent with the seat-rejoin design,
  which already assumes a room should survive everyone briefly disconnecting.
- **Broadcast had no failure isolation.** `ConnectionManager.broadcast` looped over every
  connection with no error handling; one dead/racing connection could have thrown and blocked
  delivery to everyone else. Now a failed send self-heals (disconnects that seat) instead of
  breaking the loop.

## Shoot-the-moon card swap

Resolved the step 3 gap with a mandatory, fully blind two-phase protocol, per design decisions
made with the user:

- **Mandatory, not optional** — a MOON bid always includes the swap; skipping it would make MOON
  functionally indistinguishable from ALONE at half the points.
- **Fully blind** — neither side ever learns which card the other contributed, even after the
  trade completes.
- `GameSession.call_trump` now takes a required `swap_out_card` for MOON bids (rejected for any
  other bid), stores it in a session-internal field never serialized to any client, and enters a
  new `Phase.MOON_SWAP` instead of going straight to `PLAYING`. A new `submit_moon_swap_card`
  method (only callable by the bidder's partner) performs the actual exchange and resumes play.
  A `moon_swap_turn` property (mirroring `bidder_turn`/`player_turn`) tells clients WHO needs to
  act, never WHICH card is involved.
- Frontend: `TrumpCallPanel` now requires picking a card alongside suit/high/low for MOON bids
  (a "Confirm" step); a new `MoonSwapPanel` handles the partner's response.
- `test_main.py::test_moon_swap_stays_blind_over_the_wire` exercises the full round-trip and
  asserts the swap card never appears in any payload but the two participants' own hands.

## Current test coverage
- Backend: 116 tests (`pytest`), mypy strict clean.
- Frontend: 35 tests (`vitest`), `tsc` build and `oxlint` clean.

## Not yet built (per CLAUDE.md's remaining build order)
- Step 5: Discord OAuth2 + persistent Postgres (accounts, game history, leaderboard).
- Step 6 (optional/later): rule-based bot players.
- Out of scope for now: public lobby browser, Discord-native friend invites, ML-based bots, P2P/WebRTC.
