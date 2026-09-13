interface GameOverScreenProps {
  scores: Record<number, number>;
  yourTeam: number;
}

export function GameOverScreen({ scores, yourTeam }: GameOverScreenProps) {
  const teamAScore = scores[0] ?? 0;
  const teamBScore = scores[1] ?? 0;
  const winningTeam = teamAScore > teamBScore ? 0 : 1;
  const youWon = winningTeam === yourTeam;

  return (
    <div className="game-over-screen">
      <h1>{youWon ? "Your team wins!" : "Your team lost."}</h1>
      <p>
        Team A: {teamAScore} &mdash; Team B: {teamBScore}
      </p>
    </div>
  );
}
