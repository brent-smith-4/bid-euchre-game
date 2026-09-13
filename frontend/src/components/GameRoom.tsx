import { BiddingPanel } from "./BiddingPanel";
import { GameOverScreen } from "./GameOverScreen";
import { Hand } from "./Hand";
import { Lobby } from "./Lobby";
import { ScoreBoard } from "./ScoreBoard";
import { Table } from "./Table";
import { Toast } from "./Toast";
import { TrumpCallPanel } from "./TrumpCallPanel";
import { bidLabel, playerName, suitSymbol } from "../protocol";
import { useGameSocket } from "../useGameSocket";
import { useRoundBanner } from "../useRoundBanner";

interface GameRoomProps {
  roomCode: string;
}

export function GameRoom({ roomCode }: GameRoomProps) {
  const {
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
  } = useGameSocket(roomCode);
  const roundBanner = useRoundBanner(state, yourPlayerId);

  if (status === "not_found") {
    return <div className="status-screen">Room not found — check the code and try again.</div>;
  }
  if (status === "full") {
    return <div className="status-screen">This room is full, or the game already started.</div>;
  }
  if (status === "closed") {
    return <div className="status-screen">Disconnected from the server.</div>;
  }
  if (status === "connecting" || yourPlayerId === null) {
    return <div className="status-screen">Connecting...</div>;
  }

  if (state === null) {
    if (lobbyState === null) return <div className="status-screen">Connecting...</div>;
    return (
      <Lobby
        lobbyState={lobbyState}
        yourPlayerId={yourPlayerId}
        onSwapTeam={sendSwapTeam}
        onSetTeamColor={sendSetTeamColor}
        onSetTeamName={sendSetTeamName}
        onSetTargetScore={sendSetTargetScore}
        onStartGame={sendStartGame}
      />
    );
  }

  const yourTeam = yourPlayerId % 2;
  const isYourBidTurn = state.bidder_turn === yourPlayerId;
  const isYourPlayTurn = state.player_turn === yourPlayerId;
  const isBidWinner = state.winning_bid?.player_id === yourPlayerId;

  return (
    <div className="app">
      <div className="you-are">
        Playing as <strong>{playerName(yourPlayerId)}</strong>
      </div>

      <ScoreBoard
        scores={state.scores}
        targetScore={state.target_score}
        yourTeam={yourTeam}
        teams={state.teams}
      />

      {state.phase === "GAME_OVER" ? (
        <GameOverScreen scores={state.scores} yourTeam={yourTeam} />
      ) : (
        <>
          <Table state={state} yourPlayerId={yourPlayerId} />

          <div className="trump-indicator">
            {state.trump && (
              <span>
                Trump: {state.trump.mode === "SUIT" ? suitSymbol(state.trump.suit!) : state.trump.mode}
              </span>
            )}
            {state.winning_bid && (
              <span>
                Bid: {bidLabel(state.winning_bid.rung)} by {playerName(state.winning_bid.player_id)}
              </span>
            )}
          </div>

          {state.phase === "BIDDING" && (
            <BiddingPanel yourTurn={isYourBidTurn} legalBids={state.legal_bids} onBid={sendBid} />
          )}
          {state.phase === "CALLING_TRUMP" && (
            <TrumpCallPanel isBidWinner={isBidWinner} onCallTrump={sendCallTrump} />
          )}

          <Hand
            cards={state.your_hand}
            yourTurn={state.phase === "PLAYING" && isYourPlayTurn}
            legalPlays={state.legal_plays}
            onPlay={sendPlayCard}
          />
        </>
      )}

      <Toast message={roundBanner.message} onDismiss={roundBanner.dismiss} variant="info" />
      <Toast message={error} onDismiss={dismissError} variant="error" />
    </div>
  );
}
