# Changelog

Tracks what's been built against CLAUDE.md's build order. Steps 1-4 and 6 are done — step 5
(Discord OAuth2 + Postgres accounts/history/leaderboard) was deliberately skipped; see below.

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
- `useRoundBanner` — diffs consecutive states to announce who won the bid and who won the
  trick. (Originally framed per-viewer as "You won/lost the bid!"/"Your team won/lost the
  trick!"; changed to a plain `"<name> won the bid"`/`"<name> won the trick"` format during the
  step 6 bot-pacing polish — see below.)
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

## Step 5 — skipped

Discord OAuth2 + persistent Postgres (accounts, game history, leaderboard) was deliberately
skipped rather than deferred. The project's actual goal — playing with friends online — was
already fully achieved by step 4 without any accounts; the only things step 5 would add
(persistent history, a leaderboard) are bragging-rights nice-to-haves, not the "easy 20%" CLAUDE.md
frames them as being load-bearing for. Judged low-ROI for the DS/MLE/AIE/SWE roles this portfolio
targets — real-time sync, a non-trivial rules engine, and server authority already demonstrate the
differentiated signal step 5 wouldn't meaningfully add to.

## Step 6 — Rule-based bot players (`src/bid_euchre_server/bot.py`)

No training data, no learned models, no RL — pure heuristics reusing the existing rules-engine
functions (`is_right_bower`/`is_left_bower`/`card_rank_value`/`determine_trick_winner`) rather
than re-deriving any of them. A bot is just another `player_id` taking its turn through the exact
same `GameSession` methods a human's WebSocket handler calls — `bid_euchre` (the rules engine)
has zero knowledge bots exist.

- **`choose_bid`** — estimates trick-taking strength per candidate suit (bowers/trump depth, same
  idea as the moon-swap card ranking) and separately for no-trump HIGH/LOW, where the model is
  materially different: no-trump has no bowers to fall back on, so the only reliable way to win a
  trick is holding the single best card for that suit under the mode's ordering (the "anchor" —
  ACE for HIGH, NINE for LOW). Scoring is **bid-position dependent**: the player left of the
  dealer bids first *and* leads the first trick if they win (existing rule from step 4), so only
  that seat can guarantee *when* a suit gets played by leading it themselves — anyone else needs a
  much blunter signal (3+ of the single best card, capped at a bid of THREE) since they have no
  control over the lead. MOON/ALONE are rare, gated on genuinely dominant hands, and only reachable
  by the first bidder.
- **`choose_trump`** — reuses the same per-suit/no-trump scoring `choose_bid` already computed.
- **`choose_moon_swap_card`** — trump-aware (`card_rank_value`), and deliberately diverges by
  role: as the bidder, gives away the *weakest* card (keeps strength for their own hand); as the
  partner, gives away the *strongest* (the swap's whole point is helping the bidder sweep all 6).
- **`choose_card_to_play`** — never reimplements follow-suit (only ever chooses from
  server-computed `legal_plays`). Leads the strongest card from its longest suit; when following,
  reuses `determine_trick_winner` to check whether each candidate would currently win, playing the
  cheapest winner or, failing that, the cheapest legal discard.
- `Room` gained `bot_ids`/`game_to_lobby`, `add_bot`/`remove_bot` (host-only, fills/frees the
  lowest open seat exactly like a human joining/leaving), and a `naming_rights_holder` fix so a
  bot occupying a team's lowest seat can't lock out a human teammate's naming rights.
- `main.py`'s `resolve_bot_turns` runs after every state-changing message, looping through any
  consecutive bot turns (a run of bots in a row, or spanning a hand boundary). Each bot action
  waits a real `asyncio.sleep` "thinking" delay and broadcasts individually rather than the whole
  cascade firing and broadcasting instantly — bids take 1-2s, escalating by +1s per consecutive
  bot bid in the same cascade so a run of bids doesn't feel simultaneous; trump calls, the moon
  swap card, and card plays take ~1s (0.5-1.5s). The delay ranges are module-level (not
  constants) so `test_main.py` zeroes them out for fast tests without touching the turn logic.
- Frontend: a host-only "Add bot" button in the lobby (and a "Remove" button per bot), a "(Bot)"
  label on bot-occupied seats in both the lobby and the live table.
- `try_bot_bid.py` (repo root, gitignored-worthy scratch file, not part of the test suite) — a
  small CLI for manually trying arbitrary hands against `choose_bid`/`choose_trump` by shorthand
  (`"JS KS 9S AH QD TC"`).

### Fixes found after playing against real bots
- **Bots led with trump immediately.** `choose_card_to_play`'s leading logic picked the strongest
  card from the bot's longest suit in hand — but trump is very often a bidding-team bot's longest
  suit, so a bidder's partner would burn trump the instant they took the lead instead of saving
  it. Now leads the highest *off-suit* card when any are available, only leading trump (the
  lowest held, conserving the rest) once none remain.
- **Completed tricks vanished instantly.** `GameSession.play_card` clears `current_trick` and
  reports the winner in the same atomic state transition — no broadcast ever showed all 4 played
  cards. Added `last_trick_cards`/`build_state_view`'s `last_trick` field (mirrors the existing
  `last_trick_winner` pattern: persists into the next hand's bidding, resets on the next
  `call_trump`) so the frontend's new `useTrickDisplay` hook can hold the finished trick on
  screen for 2s — imperatively via a ref-based timer, not a `useEffect` cleanup tied to state
  changes, since the latter would cancel the pending timer (without rescheduling it) the instant
  the next trick's first card arrived, leaving the table stuck showing the old trick forever.
- **Bidding cascades felt slow, and a bot's "thinking" time overlapped with the trick-hold.**
  Bid delays were tuned down to a 1-2s range (from a wider one) and card plays to a flat 1.5s
  (`CARD_PLAY_DELAY`). A bot about to lead a brand new trick now also waits `TRICK_CLEAR_DELAY`
  (2s, matching `useTrickDisplay`'s `HOLD_MS`) on top of its own `CARD_PLAY_DELAY` before acting —
  so its "thinking" timer doesn't start until the previous trick has actually finished being shown
  on screen, instead of counting down silently underneath it. `useRoundBanner` was also reworked
  to name the actual winner (`"<name> won the bid"`/`"<name> won the trick"`) instead of framing
  the message from each viewer's own "you/your team" perspective, since a per-team framing doesn't
  read naturally once the room includes bots.
- **A bot bid FOUR in diamonds holding no bowers (Q/K/A of diamonds + 1 off-suit ace), then got
  set to 2 tricks** because the opponent held both bowers and simply beat every one of those
  "high" diamonds. The original suit-mode scoring credited non-bower trump cards at meaningful
  value with no regard for whether a bower backed them up. Per the user's correction: without
  EITHER bower, nothing guards your other trump cards from whoever holds them — a suit-mode bid
  now caps at THREE with zero bowers, no matter how many of the other 5 ranks (9/10/Q/K/A) or
  extra off-suit aces the hand holds (`_NO_BOWER_SUIT_BID_CAP` in `bot.py`'s `_suit_option`; the
  per-card scoring itself is unchanged, only the final rounded estimate gets capped).

## Table UI polish — team-colored names, per-seat trick count
- **Player names are now color-coded to their team**, in both an opponent's table seat and the
  round-outcome toast, instead of being plain text a viewer has to cross-reference against the
  scoreboard. `protocol.ts` gained `teamOf`/`playerColor` helpers (mirroring
  `bid_euchre.models.team_of`'s fixed `player_id % 2` partnership split — a static seat-parity
  rule, not live game state, so computing it client-side doesn't cross CLAUDE.md's
  server-authority line the way turn/legality logic would). `useRoundBanner` was reworked again to
  return structured `{winnerId, event}` instead of a pre-built string, so `GameRoom` can render
  just the winner's name in their team's color rather than the whole toast in one plain color;
  `Toast` now accepts a `ReactNode` message instead of a bare string, and the constructed banner
  element is `useMemo`'d on `[winnerId, event, color]` so the Toast's auto-dismiss timer (keyed on
  message identity) doesn't keep resetting on every unrelated state broadcast between the human's
  screen and the bots' turns.
- **The "N cards" counter under each opponent seat now shows tricks taken this hand instead.**
  Card count was redundant with a well-understood 6-card starting hand and told you nothing about
  how the hand was actually going; a running per-seat trick count does. `GameSession` gained
  `tricks_won_by_player` (mirrors the existing per-team `_tricks_won`, reset in the same
  `_begin_trick_play` and incremented alongside it in `play_card`), threaded into
  `build_state_view` as `tricks_won` and consumed by `Table`/`Seat`.

## Rule change — MOON's partner sits out too
- **MOON now plays exactly like ALONE: the bidder's partner does not play any cards, only the
  pre-play blind swap.** Originally (and per CLAUDE.md's original text) MOON's partner played
  normally after the swap; the user decided in testing that read wrong and asked for parity with
  ALONE. `trick.py`'s `active_players`/`trick_play_order` now exclude the partner for both
  `BidRung.MOON` and `BidRung.ALONE` (`_SOLO_RUNGS`) instead of ALONE alone. The only remaining
  differences between the two bids are the swap itself and the point value (12 vs 24) — MOON is
  now "ALONE, but your partner hands you one assist card first, for half the points."
  Investigated but could **not** reproduce a separate bug report that ALONE's partner was already
  playing — drove full ALONE hands through both `GameSession` directly and the real WS + bot
  layer, and the partner never got a turn in either case. Added regression tests at all 3 layers
  (`test_trick.py`, `test_session.py`, `test_main.py`) covering both MOON and ALONE. Frontend:
  `GameRoom` now hides the generic `Hand` panel and shows a "You're sitting out this hand" note
  for the MOON/ALONE partner during `PLAYING`, instead of rendering their hand as a normal-looking
  but silently inert set of cards.

## Game length presets — Normal/Quick/Test
- **The lobby's numeric "Target score" input became a "Game Length" selector** offering three
  presets, each fixing both the match's target score and what MOON/ALONE pay out for its whole
  duration: Normal (52 to win, MOON 12/ALONE 24 — unchanged from before), Quick (24 to win, MOON
  7/ALONE 12), and a dev-only Test preset (6 to win, MOON/ALONE both 6) for quickly exercising the
  win-condition path — marked with a `# Dev-only - comment out before deploying.` comment on both
  the backend (`room.GAME_LENGTHS`) and frontend (`protocol.GAME_LENGTH_OPTIONS`) entries, a
  one-line removal rather than a feature flag.
- `bid_euchre.scoring.score_hand` now takes optional `moon_points`/`alone_points` (defaulting to
  the old module constants, so every existing call site and test is unaffected);
  `GameSession`/`Room` thread the selected preset's values through to it. The wire protocol's
  `lobby_state`/`state` payloads carry `game_length`/`target_score`/`moon_points`/`alone_points`,
  and `BiddingPanel`'s bid-button point labels now read from the server's values instead of a
  hardcoded "12 pts"/"24 pts" — keeps the client from having its own opinion about what a bid is
  worth, per CLAUDE.md's server-authority principle.
- The selected preset renders as a row of pill buttons rather than a dropdown/number field, with
  the active one styled to look physically pressed in (inset shadow, slight downward shift) rather
  than just a color change.

## Host controls — Finish game
- **The host can end an in-progress match early via a "Finish game" button**, sending everyone
  back to that same room's lobby with teams, colors, bots, and the previously-picked game length
  intact (`Room.finish_game`, gated to `IN_GAME` + host-only, mirroring `restart_game`'s shape).
  Hidden once a match reaches `GAME_OVER`, since that screen already has its own "Play again"/Home
  controls.
- **Fixed a WS dispatch bug this surfaced**: `finish_game`/`restart_game` were only checked *after*
  confirming `room.status is IN_GAME`, so a message that arrived just as the room had already
  flipped back to `LOBBY` (a duplicate click queued behind a bot's "thinking" delay, say) fell
  through to the lobby-only message handler and came back as a confusing "unknown message type"
  instead of the intended "not in a game." Both message types are now recognized regardless of
  room status.
- **Fixed the deeper cause of that queuing**: `resolve_bot_turns` used to be `await`ed inline in
  the same connection's message loop, so a bot's "thinking" `asyncio.sleep` blocked that connection
  from reading *any* new incoming message — including Finish Game — until the entire bot cascade
  finished. It now runs as a background task (`schedule_bot_turns`, one per room, tracked so a
  second trigger while one's in flight is a no-op), so a host action takes effect immediately no
  matter what bots are doing. A companion staleness guard makes an orphaned cascade quietly stop
  (rather than acting/broadcasting on an abandoned match) if `finish_game`/`restart_game` swaps
  `room.session` out from under it mid-sleep. `GameRoom`'s Finish Game button also disables itself
  and shows "Finishing..." immediately on click, so there's no reason to click it twice while
  waiting out a bot delay in the first place.
- `useGameSocket` previously never reset its `state` back to `null` on a `lobby_state` message —
  harmless while rooms only ever went lobby→game, but would have left the old game screen frozen
  on screen after `finish_game` sent the room back to `LOBBY`. Fixed alongside the button.

## Lobby UI polish
- **Team panels are always sized for a full team (2 seats each)** instead of growing as
  players/bots join — empty seats render as a dashed, italicized "Open seat" placeholder so the
  room looks like it did with all 4 seats filled from the moment it's created.
- **Host action buttons (Add bot / Start game / Leave room) are grouped into one row**, and the
  "need more players" hint simplified from "Need 2 players on each team to start (4 total) -
  currently X on Team A, Y on Team B" to "Need 4 players to start (have N)."

## Dev environment fix
- The frontend's `HTTP_BASE`/`WS_BASE` defaults changed from `localhost:8000` to `127.0.0.1:8000`.
  uvicorn only binds the IPv4 loopback; resolving `localhost` made the browser waste time on a
  doomed IPv6 (`::1`) attempt before falling back, adding a consistent ~200ms+ delay to every
  request and WebSocket connection on Windows.

## Table/card visual overhaul
- **Real playing-card visuals** — `PlayingCard` now draws proper corner indices (rank+suit
  stacked top-left, mirrored bottom-right) around a large centered suit pip, instead of a plain
  centered rank/suit stack. Every card everywhere (hand, trick area, moon-swap, trump-call) picks
  this up automatically since they all share the one component. Diamond/heart suit symbols are
  red (`#c02020`, matching the card faces) everywhere a suit renders standalone too — the trump
  indicator ("Trump: ♦") and the Call Trump suit buttons.
- **Shuffle-and-deal animation** — a new `useDealAnimation` hook detects the start of a fresh hand
  (the dealer seat rotates, no bids/tricks yet - every hand's dealer strictly increments, so this
  is unambiguous without the server announcing it as its own event) and plays a ~2.5s overlay of
  small flying card-backs, dealt clockwise from the seat left of the dealer, 2 at a time, until
  all 24 are out. The ref that tracks "the last dealer we saw" is seeded with an impossible
  sentinel (`-1`) rather than `null`, so the very first hand of a match animates too, not just the
  second hand onward. Both the on-table seat card fans *and* the interactive hand panel below the
  table reveal in step with the animation (via the hook's `revealedCounts`) instead of jumping to
  the real, already-fully-dealt hand size the instant the state arrives - `useDealAnimation` is
  called once in `GameRoom` and passed down to `Table`, rather than called separately in each, so
  both stay in sync off the same clock.
- **Every seat shows its cards on the table** — face-down backs sized to hand count for
  opponents/teammate, face-up mini cards for you, in addition to (not instead of) the existing
  interactive hand panel below the table.
- **Trick-winner sweep animation** — once a trick completes, the 4 played cards hold face-up for
  the first 1.4s of the existing 2s display window, then flip face-down and fly toward the
  winner's seat while fading out, finishing right as the hold ends (no snap). Found and fixed a
  real CSS bug here during testing: the keyframe listed `rotateY(180deg) translate(x, y)` - since
  transform functions compose right-to-left, that made the *rotation* the outer transform, which
  negates the X-axis translation afterward and silently mirrored every left/right sweep (a trick
  Bravo/left won would visibly sweep toward Delta/right instead). Reordering to
  `translate(x, y) rotateY(180deg)` keeps the translate anchored to the original, unrotated axes.
  Top/bottom sweeps were never affected, since rotateY only flips X and Z.
- **Table is taller and more stylized** — `min-height: clamp(340px, 58vh, 560px)` (was a flat
  260px) so it shrinks on short viewports instead of forcing a fixed height regardless of
  available space, oval-ish rounded corners, a brown rail (`--table-rail`, kept separate from the
  app's gold `--accent` so only the table trim changed) instead of gold, and a radial felt
  gradient instead of a flat color.
- **Bid/trump status moved above the table**, directly under the scoreboard, instead of between
  the table and the bid/trump-call panel.
- **Bid prompt copy**: "Your Bid: # of tricks you think your team can take." Legend copy split
  into two lines: "Shoot the Moon: 6 tricks solo, partner card swap" / "Go Alone: 6 tricks solo."

## Current test coverage
- Backend: 148 tests (`pytest`), mypy strict clean. Includes a 500-hand fuzz test asserting
  `choose_card_to_play` never produces an illegal card, end-to-end WebSocket tests where a lone
  human plus 3 bots resolve an entire bidding round on their own, where MOON/ALONE's partner never
  gets a turn over the real WS layer, and where `finish_game` resolves immediately rather than
  queuing behind a real (non-zeroed) bot "thinking" delay.
- Frontend: 44 tests (`vitest`), `tsc` build and `oxlint` clean.

## Out of scope for now
- Public lobby browser, Discord-native friend invites, ML-based bots, P2P/WebRTC (per CLAUDE.md).
