import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE } from "./config";
import type { BidRung, Card, ClientMessage, LobbyState, ServerMessage, StateView, Suit, TrumpMode } from "./protocol";
import { describeError } from "./protocol";

export type ConnectionStatus = "connecting" | "open" | "closed" | "full" | "not_found";

const ROOM_FULL_MESSAGES = new Set(["all 4 seats are taken", "game already in progress"]);

export interface GameSocket {
  status: ConnectionStatus;
  yourPlayerId: number | null;
  lobbyState: LobbyState | null;
  state: StateView | null;
  error: string | null;
  sendBid: (rung: BidRung) => void;
  sendCallTrump: (mode: TrumpMode, suit: Suit | null) => void;
  sendPlayCard: (card: Card) => void;
  sendSwapTeam: (withPlayerId: number) => void;
  sendSetTeamColor: (team: number, color: string) => void;
  sendSetTeamName: (team: number, name: string) => void;
  sendSetTargetScore: (value: number) => void;
  sendStartGame: () => void;
  dismissError: () => void;
}

// Owns the WebSocket connection lifecycle for one room. The server is the
// sole source of truth for both lobby and game state: every incoming
// "lobby_state"/"state" message fully replaces the prior one (no
// client-side merging or optimistic updates), per CLAUDE.md's
// server-authority principle.
//
// A player's id can differ between the lobby (assigned by connection order)
// and the game (assigned by team once the host starts it) - every
// lobby_state/state message carries its own your_player_id, and this hook
// re-syncs from it every time rather than trusting the one-time
// "assigned_seat" announcement alone.
export function useGameSocket(roomCode: string | null): GameSocket {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [yourPlayerId, setYourPlayerId] = useState<number | null>(null);
  const [lobbyState, setLobbyState] = useState<LobbyState | null>(null);
  const [state, setState] = useState<StateView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (roomCode === null) return;

    const socket = new WebSocket(`${WS_BASE}/ws/${roomCode}`);
    socketRef.current = socket;

    socket.onopen = () => setStatus("open");
    socket.onclose = () => setStatus((prev) => (prev === "open" || prev === "connecting" ? "closed" : prev));

    socket.onmessage = (event: MessageEvent<string>) => {
      const message = JSON.parse(event.data) as ServerMessage;
      if (message.type === "assigned_seat") {
        setYourPlayerId(message.player_id);
      } else if (message.type === "lobby_state") {
        setYourPlayerId(message.your_player_id);
        setLobbyState(message);
      } else if (message.type === "state") {
        setYourPlayerId(message.your_player_id);
        setState(message);
      } else if (message.type === "error") {
        if (ROOM_FULL_MESSAGES.has(message.message)) {
          setStatus("full");
        } else if (message.message === "room not found") {
          setStatus("not_found");
        } else {
          setError(describeError(message.message));
        }
      }
    };

    return () => socket.close();
  }, [roomCode]);

  const send = useCallback((message: ClientMessage) => {
    socketRef.current?.send(JSON.stringify(message));
  }, []);

  const sendBid = useCallback((rung: BidRung) => send({ type: "bid", rung }), [send]);
  const sendCallTrump = useCallback(
    (mode: TrumpMode, suit: Suit | null) => send({ type: "call_trump", mode, suit }),
    [send],
  );
  const sendPlayCard = useCallback((card: Card) => send({ type: "play_card", card }), [send]);
  const sendSwapTeam = useCallback(
    (withPlayerId: number) => send({ type: "swap_team", with_player_id: withPlayerId }),
    [send],
  );
  const sendSetTeamColor = useCallback(
    (team: number, color: string) => send({ type: "set_team_color", team, color }),
    [send],
  );
  const sendSetTeamName = useCallback(
    (team: number, name: string) => send({ type: "set_team_name", team, name }),
    [send],
  );
  const sendSetTargetScore = useCallback(
    (value: number) => send({ type: "set_target_score", value }),
    [send],
  );
  const sendStartGame = useCallback(() => send({ type: "start_game" }), [send]);
  const dismissError = useCallback(() => setError(null), []);

  return {
    status,
    yourPlayerId,
    lobbyState,
    state,
    error,
    sendBid,
    sendCallTrump,
    sendPlayCard,
    sendSwapTeam,
    sendSetTeamColor,
    sendSetTeamName,
    sendSetTargetScore,
    sendStartGame,
    dismissError,
  };
}
