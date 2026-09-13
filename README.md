# Bid Euchre

A real-time, server-authoritative multiplayer implementation of Bid Euchre — a bidding-and-tricks
card game played in fixed 2v2 partnerships. Create a room, share the code with three other
players, and play a full match live over WebSockets.

## Features

- **Room-code lobbies.** Create a room, get a short shareable code, and up to 4 players join by
  code — no accounts needed yet. Multiple rooms run concurrently and don't interfere.
- **Team selection.** Players freely swap between the two teams, each team picks a color and an
  optional name, and the host sets the target score before starting.
- **Full bid euchre rules**, including the stuck-dealer forced bid, trump calling (suit, or
  no-trump high/low), bower ranking, shoot-the-moon and going-alone bids, and standard scoring.
- **Live, legality-gated UI.** Illegal bids and illegal card plays are greyed out client-side
  using the exact same legality checks the server enforces — never a separately-invented set of
  client-side rules.
- **Seat-based rejoin.** If your connection drops mid-game, reopening the room reclaims your seat
  instead of stranding the match.

See [CHANGELOG.md](CHANGELOG.md) for a detailed, step-by-step breakdown of what's been built (and
the bugs found and fixed along the way).

## Tech stack

- **Backend:** Python, FastAPI + native WebSocket support. Type-hinted throughout, checked with
  `mypy --strict`.
- **Frontend:** React + TypeScript, built with Vite. No UI framework dependency — plain CSS.
- **Testing:** `pytest` (backend), `vitest` + React Testing Library (frontend).

## Project structure

```
src/bid_euchre/          Standalone rules engine (no networking): bidding, ranking, trick
                          resolution, scoring. Fully unit-tested in isolation.
src/bid_euchre_server/   FastAPI app: room/lobby management, WebSocket wiring, the
                          GameSession turn orchestrator built on top of bid_euchre.
tests/                   pytest suite for both packages above.
frontend/                Vite + React + TypeScript client.
CHANGELOG.md             What's been built, step by step.
```

## Running it locally

You'll need Python 3.11+ and Node 20+.

### Backend

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn bid_euchre_server.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`). Create a room, then open the room
URL in 3 more tabs (or share it with friends) to fill out a 4-player match.

## Running the tests

```bash
# backend, from the repo root
pytest
mypy src

# frontend
cd frontend
npm run test
npm run build   # also type-checks
npm run lint
```

## Status

Steps 1-4 of the build order are complete: the rules engine, the WebSocket server, the React
frontend, and room-code lobbies. Not yet built: Discord OAuth2 + persistent accounts/history/
leaderboard (step 5), and optional rule-based bot players (step 6).
