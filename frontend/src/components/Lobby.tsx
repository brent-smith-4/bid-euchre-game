import { useState } from "react";
import type { LobbyState } from "../protocol";
import { playerName } from "../protocol";

interface LobbyProps {
  lobbyState: LobbyState;
  yourPlayerId: number;
  onSwapTeam: (withPlayerId: number) => void;
  onSetTeamColor: (team: number, color: string) => void;
  onSetTeamName: (team: number, name: string) => void;
  onSetTargetScore: (value: number) => void;
  onStartGame: () => void;
  onAddBot: () => void;
  onRemoveBot: (botId: number) => void;
  onLeaveRoom: () => void;
}

const TEAM_IDS = [0, 1];

export function Lobby({
  lobbyState,
  yourPlayerId,
  onSwapTeam,
  onSetTeamColor,
  onSetTeamName,
  onSetTargetScore,
  onStartGame,
  onAddBot,
  onRemoveBot,
  onLeaveRoom,
}: LobbyProps) {
  const yourTeam = lobbyState.players[yourPlayerId];
  const teamCounts = TEAM_IDS.map(
    (t) => Object.values(lobbyState.players).filter((team) => team === t).length,
  );
  const canStart = teamCounts.every((count) => count === 2);
  const isHost = yourPlayerId === lobbyState.host_id;
  const seatedCount = Object.keys(lobbyState.players).length;

  return (
    <div className="lobby">
      <h1>Room {lobbyState.room_code}</h1>
      <p className="lobby-hint">Share this code with the other players.</p>

      <div className="lobby-teams">
        {TEAM_IDS.map((teamId) => (
          <TeamPanel
            key={teamId}
            teamId={teamId}
            lobbyState={lobbyState}
            yourPlayerId={yourPlayerId}
            yourTeam={yourTeam}
            isHost={isHost}
            onSwapTeam={onSwapTeam}
            onSetTeamColor={onSetTeamColor}
            onSetTeamName={onSetTeamName}
            onRemoveBot={onRemoveBot}
          />
        ))}
      </div>

      <div className="lobby-host-controls">
        {isHost ? (
          <>
            <label>
              Target score:{" "}
              <input
                type="number"
                min={1}
                defaultValue={lobbyState.target_score}
                onBlur={(e) => {
                  const value = Number(e.target.value);
                  if (value > 0) onSetTargetScore(value);
                }}
              />
            </label>
            <button type="button" disabled={seatedCount >= 4} onClick={onAddBot}>
              Add bot
            </button>
            <button type="button" disabled={!canStart} onClick={onStartGame}>
              Start game
            </button>
            {!canStart && (
              <p className="lobby-hint">
                Need 2 players on each team to start (4 total) - currently {teamCounts[0]} on Team A,{" "}
                {teamCounts[1]} on Team B.
              </p>
            )}
          </>
        ) : (
          <p className="lobby-hint">
            Target score: {lobbyState.target_score}. Waiting for the host to start the game...
          </p>
        )}
        <button type="button" onClick={onLeaveRoom}>
          Leave room
        </button>
      </div>
    </div>
  );
}

interface TeamPanelProps {
  teamId: number;
  lobbyState: LobbyState;
  yourPlayerId: number;
  yourTeam: number | undefined;
  isHost: boolean;
  onSwapTeam: (withPlayerId: number) => void;
  onSetTeamColor: (team: number, color: string) => void;
  onSetTeamName: (team: number, name: string) => void;
  onRemoveBot: (botId: number) => void;
}

function TeamPanel({
  teamId,
  lobbyState,
  yourPlayerId,
  yourTeam,
  isHost,
  onSwapTeam,
  onSetTeamColor,
  onSetTeamName,
  onRemoveBot,
}: TeamPanelProps) {
  const team = lobbyState.teams[teamId];
  const members = Object.entries(lobbyState.players)
    .filter(([, t]) => t === teamId)
    .map(([id]) => Number(id));
  const youAreOnThisTeam = yourTeam === teamId;
  const canRenameThisTeam = yourPlayerId === team.naming_rights_holder;
  const [draftName, setDraftName] = useState(team.name ?? "");

  return (
    <div className="team-panel" style={{ borderColor: team.color }}>
      <input
        type="color"
        value={team.color}
        disabled={!youAreOnThisTeam}
        onChange={(e) => onSetTeamColor(teamId, e.target.value)}
      />
      <input
        type="text"
        placeholder={`Team ${teamId === 0 ? "A" : "B"}`}
        value={draftName}
        disabled={!canRenameThisTeam}
        onChange={(e) => setDraftName(e.target.value)}
        onBlur={() => onSetTeamName(teamId, draftName)}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
      />
      <ul>
        {members.map((playerId) => {
          const isBot = lobbyState.bots.includes(playerId);
          return (
            <li key={playerId}>
              {playerName(playerId)}
              {isBot && " (Bot)"}
              {!isBot && playerId === yourPlayerId && " (you)"}
              {!youAreOnThisTeam && yourTeam !== undefined && (
                <button type="button" onClick={() => onSwapTeam(playerId)}>
                  Swap with me
                </button>
              )}
              {isBot && isHost && (
                <button type="button" onClick={() => onRemoveBot(playerId)}>
                  Remove
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
