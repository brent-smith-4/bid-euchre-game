import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LobbyState } from "../protocol";
import { Lobby } from "./Lobby";

function makeLobby(overrides: Partial<LobbyState> = {}): LobbyState {
  return {
    type: "lobby_state",
    room_code: "ABC123",
    your_player_id: 0,
    host_id: 0,
    game_length: "normal",
    target_score: 52,
    moon_points: 12,
    alone_points: 24,
    players: { 0: 0, 1: 1, 2: 0, 3: 1 },
    player_names: {},
    teams: {
      0: { color: "#0a84ff", name: null, naming_rights_holder: 0 },
      1: { color: "#ff3b30", name: null, naming_rights_holder: 1 },
    },
    bots: [],
    ...overrides,
  };
}

function noop() {}

const commonHandlers = {
  onSwapTeam: noop,
  onSetTeamColor: noop,
  onSetTeamName: noop,
  onSetGameLength: noop,
  onStartGame: noop,
  onAddBot: noop,
  onRemoveBot: noop,
  onLeaveRoom: noop,
  onSetPlayerName: noop,
};

describe("Lobby", () => {
  it("lets a player swap onto the other team and reports who they swap with", () => {
    const onSwapTeam = vi.fn();
    render(
      <Lobby lobbyState={makeLobby()} yourPlayerId={0} {...commonHandlers} onSwapTeam={onSwapTeam} />,
    );

    // player 0 is on team 0; only players on team 1 (Bravo, Delta) get a swap button.
    const swapButtons = screen.getAllByRole("button", { name: /^swap$/i });
    expect(swapButtons).toHaveLength(2);

    fireEvent.click(swapButtons[0]);
    expect(onSwapTeam).toHaveBeenCalledWith(1);
  });

  it("only enables a team's color select for players seated on that team", () => {
    render(<Lobby lobbyState={makeLobby()} yourPlayerId={0} {...commonHandlers} />);

    const colorSelects = document.querySelectorAll("select");
    expect(colorSelects).toHaveLength(2);
    expect(colorSelects[0]).toBeEnabled(); // team 0 - you're on it
    expect(colorSelects[1]).toBeDisabled(); // team 1 - you're not
  });

  it("only enables a team's name input for that team's naming-rights holder", () => {
    render(
      <Lobby lobbyState={makeLobby({ your_player_id: 2 })} yourPlayerId={2} {...commonHandlers} />,
    );

    // player 2 is on team 0, but naming rights belong to player 0.
    const nameInputs = screen.getAllByPlaceholderText(/^team [ab]$/i);
    expect(nameInputs[0]).toBeDisabled();
    expect(nameInputs[1]).toBeDisabled();
  });

  it("shows host controls only to the host, and disables start until teams are 2v2", () => {
    const onStartGame = vi.fn();
    const { rerender } = render(
      <Lobby
        lobbyState={makeLobby({ players: { 0: 0, 1: 1, 2: 0 } })}
        yourPlayerId={0}
        {...commonHandlers}
        onStartGame={onStartGame}
      />,
    );
    expect(screen.getByRole("button", { name: /start game/i })).toBeDisabled();

    rerender(
      <Lobby lobbyState={makeLobby()} yourPlayerId={0} {...commonHandlers} onStartGame={onStartGame} />,
    );
    const startButton = screen.getByRole("button", { name: /start game/i });
    expect(startButton).toBeEnabled();
    fireEvent.click(startButton);
    expect(onStartGame).toHaveBeenCalled();
  });

  it("shows a waiting message instead of host controls for non-hosts", () => {
    render(
      <Lobby lobbyState={makeLobby({ your_player_id: 1 })} yourPlayerId={1} {...commonHandlers} />,
    );
    expect(screen.queryByRole("button", { name: /start game/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add bot/i })).not.toBeInTheDocument();
    expect(screen.getByText(/waiting for the host/i)).toBeInTheDocument();
  });

  it("lets only the host add a bot, disabled once the room is full", () => {
    const onAddBot = vi.fn();
    const { rerender } = render(
      <Lobby
        lobbyState={makeLobby({ players: { 0: 0, 1: 1, 2: 0 } })}
        yourPlayerId={0}
        {...commonHandlers}
        onAddBot={onAddBot}
      />,
    );
    const addBotButton = screen.getByRole("button", { name: /add bot/i });
    expect(addBotButton).toBeEnabled();
    fireEvent.click(addBotButton);
    expect(onAddBot).toHaveBeenCalled();

    rerender(
      <Lobby lobbyState={makeLobby()} yourPlayerId={0} {...commonHandlers} onAddBot={onAddBot} />,
    );
    expect(screen.getByRole("button", { name: /add bot/i })).toBeDisabled(); // 4 seats full
  });

  it("shows a Bot label and a host-only remove button for bot-occupied seats", () => {
    const onRemoveBot = vi.fn();
    const lobby = makeLobby({ bots: [1] });

    const { rerender } = render(
      <Lobby lobbyState={lobby} yourPlayerId={0} {...commonHandlers} onRemoveBot={onRemoveBot} />,
    );
    expect(screen.getByText(/\(Bot\)/)).toBeInTheDocument();
    const removeButton = screen.getByRole("button", { name: /remove/i });
    fireEvent.click(removeButton);
    expect(onRemoveBot).toHaveBeenCalledWith(1);

    // a non-host seated on a different team sees no remove button for the bot.
    rerender(
      <Lobby lobbyState={lobby} yourPlayerId={2} {...commonHandlers} onRemoveBot={onRemoveBot} />,
    );
    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });
});
