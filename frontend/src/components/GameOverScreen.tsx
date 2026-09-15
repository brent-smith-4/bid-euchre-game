import type { TeamMeta } from "../protocol";
import { teamLabel } from "../protocol";

interface GameOverScreenProps {
  scores: Record<number, number>;
  yourTeam: number;
  teams: Record<number, TeamMeta>;
  isHost: boolean;
  onRestartGame: () => void;
  onGoHome: () => void;
}

export function GameOverScreen({
  scores,
  yourTeam,
  teams,
  isHost,
  onRestartGame,
  onGoHome,
}: GameOverScreenProps) {
  const teamAScore = scores[0] ?? 0;
  const teamBScore = scores[1] ?? 0;
  const winningTeam = teamAScore > teamBScore ? 0 : 1;
  const youWon = winningTeam === yourTeam;

  return (
    <div className="game-over-screen">
      <h1>{youWon ? "Your team wins!" : "Your team lost."}</h1>
      <div className="game-over-scores">
        {[0, 1].map((teamId) => (
          <div key={teamId} style={{ color: teams[teamId]?.color }}>
            {teamLabel(teams, teamId)}: {scores[teamId] ?? 0}
          </div>
        ))}
      </div>

      <div className="game-over-actions">
        {isHost ? (
          <button type="button" onClick={onRestartGame}>
            Play again
          </button>
        ) : (
          <p className="lobby-hint">Waiting for the host to start a new match...</p>
        )}
        <button type="button" onClick={onGoHome}>
          Home
        </button>
      </div>
    </div>
  );
}
