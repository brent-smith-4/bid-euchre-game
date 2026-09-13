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
    target_score: 52,
    players: { 0: 0, 1: 1, 2: 0, 3: 1 },
    teams: {
      0: { color: "#3366cc", name: null, naming_rights_holder: 0 },
      1: { color: "#cc3333", name: null, naming_rights_holder: 1 },
    },
    ...overrides,
  };
}

function noop() {}

describe("Lobby", () => {
  it("lets a player swap onto the other team and reports who they swap with", () => {
    const onSwapTeam = vi.fn();
    render(
      <Lobby
        lobbyState={makeLobby()}
        yourPlayerId={0}
        onSwapTeam={onSwapTeam}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={noop}
      />,
    );

    // player 0 is on team 0; only players on team 1 (Bravo, Delta) get a swap button.
    const swapButtons = screen.getAllByRole("button", { name: /swap with me/i });
    expect(swapButtons).toHaveLength(2);

    fireEvent.click(swapButtons[0]);
    expect(onSwapTeam).toHaveBeenCalledWith(1);
  });

  it("only enables a team's color input for players seated on that team", () => {
    render(
      <Lobby
        lobbyState={makeLobby()}
        yourPlayerId={0}
        onSwapTeam={noop}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={noop}
      />,
    );

    const colorInputs = document.querySelectorAll('input[type="color"]');
    expect(colorInputs).toHaveLength(2);
    expect(colorInputs[0]).toBeEnabled(); // team 0 - you're on it
    expect(colorInputs[1]).toBeDisabled(); // team 1 - you're not
  });

  it("only enables a team's name input for that team's naming-rights holder", () => {
    render(
      <Lobby
        lobbyState={makeLobby({ your_player_id: 2 })}
        yourPlayerId={2}
        onSwapTeam={noop}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={noop}
      />,
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
        onSwapTeam={noop}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={onStartGame}
      />,
    );
    expect(screen.getByRole("button", { name: /start game/i })).toBeDisabled();

    rerender(
      <Lobby
        lobbyState={makeLobby()}
        yourPlayerId={0}
        onSwapTeam={noop}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={onStartGame}
      />,
    );
    const startButton = screen.getByRole("button", { name: /start game/i });
    expect(startButton).toBeEnabled();
    fireEvent.click(startButton);
    expect(onStartGame).toHaveBeenCalled();
  });

  it("shows a waiting message instead of host controls for non-hosts", () => {
    render(
      <Lobby
        lobbyState={makeLobby({ your_player_id: 1 })}
        yourPlayerId={1}
        onSwapTeam={noop}
        onSetTeamColor={noop}
        onSetTeamName={noop}
        onSetTargetScore={noop}
        onStartGame={noop}
      />,
    );
    expect(screen.queryByRole("button", { name: /start game/i })).not.toBeInTheDocument();
    expect(screen.getByText(/waiting for the host/i)).toBeInTheDocument();
  });
});
