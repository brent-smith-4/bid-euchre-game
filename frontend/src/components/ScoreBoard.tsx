import type { TeamMeta } from "../protocol";
import { teamLabel } from "../protocol";

interface ScoreBoardProps {
  scores: Record<number, number>;
  targetScore: number;
  yourTeam: number;
  teams: Record<number, TeamMeta>;
}

// TEAM_A = 0, TEAM_B = 1 (team_of in models.py: player_id % 2).
export function ScoreBoard({ scores, targetScore, yourTeam, teams }: ScoreBoardProps) {
  return (
    <div className="score-board">
      {[0, 1].map((teamId) => (
        <div
          key={teamId}
          className={yourTeam === teamId ? "your-team" : ""}
          style={{ color: teams[teamId]?.color }}
        >
          {teamLabel(teams, teamId)}: {scores[teamId] ?? 0}
        </div>
      ))}
      <div className="target">Target: {targetScore}</div>
    </div>
  );
}
