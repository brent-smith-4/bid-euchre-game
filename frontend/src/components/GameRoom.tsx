import { useMemo } from "react";
import { BiddingPanel } from "./BiddingPanel";
import { GameOverScreen } from "./GameOverScreen";
import { Hand } from "./Hand";
import { Lobby } from "./Lobby";
import { MoonSwapPanel } from "./MoonSwapPanel";
import { ScoreBoard } from "./ScoreBoard";
import { Table } from "./Table";
import { Toast } from "./Toast";
import { TrumpCallPanel } from "./TrumpCallPanel";
import { bidLabel, partnerOf, playerColor, playerName, suitSymbol } from "../protocol";
import { useGameSocket } from "../useGameSocket";
import { useRoundBanner } from "../useRoundBanner";
import { useTrickDisplay } from "../useTrickDisplay";

interface GameRoomProps {
  roomCode: string;
  onGoHome: () => void;
}

export function GameRoom({ roomCode, onGoHome }: GameRoomProps) {
  const {
    status,
    yourPlayerId,
    lobbyState,
    state,
    error,
    sendBid,
    sendCallTrump,
    sendSubmitMoonSwapCard,
    sendPlayCard,
    sendSwapTeam,
    sendSetTeamColor,
    sendSetTeamName,
    sendSetPlayerName,
    sendSetTargetScore,
    sendStartGame,
    sendAddBot,
    sendRemoveBot,
    sendRestartGame,
    dismissError,
  } = useGameSocket(roomCode);
  const roundBanner = useRoundBanner(state);
  const displayedTrick = useTrickDisplay(state);
  const bannerWinnerId = roundBanner.winnerId;
  const bannerEvent = roundBanner.event;
  const bannerColor =
    bannerWinnerId !== null && state !== null ? playerColor(state.teams, bannerWinnerId) : null;
  const bannerName = bannerWinnerId !== null ? playerName(bannerWinnerId, state?.player_names) : null;
  // Memoized so the Toast's auto-dismiss timer (keyed on message identity)
  // doesn't reset on every unrelated state broadcast - only when the
  // winner/event this banner is announcing actually changes. bannerName is
  // a primitive string (not the state.player_names object itself), so it
  // only changes value when the winner's actual display name does.
  const roundBannerMessage = useMemo(() => {
    if (bannerWinnerId === null || bannerEvent === null || bannerColor === null || bannerName === null) {
      return null;
    }
    return (
      <>
        <span style={{ color: bannerColor }}>{bannerName}</span> won the {bannerEvent}
      </>
    );
  }, [bannerWinnerId, bannerEvent, bannerColor, bannerName]);

  if (status === "not_found") {
    return (
      <div className="status-screen status-screen-column">
        <p>Room not found - check the code and try again.</p>
        <button type="button" className="felt-button" onClick={onGoHome}>
          Home
        </button>
      </div>
    );
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
        onSetPlayerName={sendSetPlayerName}
        onSetTargetScore={sendSetTargetScore}
        onStartGame={sendStartGame}
        onAddBot={sendAddBot}
        onRemoveBot={sendRemoveBot}
        onLeaveRoom={onGoHome}
      />
    );
  }

  const yourTeam = yourPlayerId % 2;
  const isYourBidTurn = state.bidder_turn === yourPlayerId;
  const isYourPlayTurn = state.player_turn === yourPlayerId;
  const isBidWinner = state.winning_bid?.player_id === yourPlayerId;
  const isMoonBid = state.winning_bid?.rung === "MOON";
  const isAloneBid = state.winning_bid?.rung === "ALONE";
  const isYourMoonSwapTurn = state.moon_swap_turn === yourPlayerId;
  // MOON and ALONE both play the bidder solo - their partner sits out the
  // hand entirely (MOON's partner only contributes the pre-play blind
  // swap). Server-side this already falls out of GameSession.player_turn
  // never landing on the sitting-out seat, but the generic Hand panel would
  // otherwise still render their cards as an inert, unexplained hand.
  const isSittingOutPartner =
    (isMoonBid || isAloneBid) &&
    state.winning_bid !== null &&
    yourPlayerId === partnerOf(state.winning_bid.player_id);
  // Hide the generic hand display while TrumpCallPanel/MoonSwapPanel are
  // already showing an interactive card-picker for this viewer, so the
  // same cards don't render twice on screen - or while sitting out a
  // MOON/ALONE hand entirely.
  const hideGenericHand =
    state.phase === "MOON_SWAP" ||
    (state.phase === "CALLING_TRUMP" && isMoonBid && isBidWinner) ||
    (state.phase === "PLAYING" && isSittingOutPartner);

  return (
    <div className="app">
      <div className="you-are">
        Playing as <strong>{playerName(yourPlayerId, state?.player_names)}</strong>
      </div>

      <ScoreBoard
        scores={state.scores}
        targetScore={state.target_score}
        yourTeam={yourTeam}
        teams={state.teams}
      />

      {state.phase === "GAME_OVER" ? (
        <GameOverScreen
          scores={state.scores}
          yourTeam={yourTeam}
          teams={state.teams}
          isHost={state.is_host}
          onRestartGame={sendRestartGame}
          onGoHome={onGoHome}
        />
      ) : (
        <>
          <Table state={state} yourPlayerId={yourPlayerId} displayedTrick={displayedTrick} />

          <div className="trump-indicator">
            {state.trump && (
              <span>
                Trump: {state.trump.mode === "SUIT" ? suitSymbol(state.trump.suit!) : state.trump.mode}
              </span>
            )}
            {state.winning_bid && (
              <span>
                Bid: {bidLabel(state.winning_bid.rung)} by{" "}
                {playerName(state.winning_bid.player_id, state.player_names)}
              </span>
            )}
          </div>

          {state.phase === "BIDDING" && (
            <BiddingPanel yourTurn={isYourBidTurn} legalBids={state.legal_bids} onBid={sendBid} />
          )}
          {state.phase === "CALLING_TRUMP" && (
            <TrumpCallPanel
              isBidWinner={isBidWinner}
              isMoonBid={isMoonBid}
              yourHand={state.your_hand}
              onCallTrump={sendCallTrump}
            />
          )}
          {state.phase === "MOON_SWAP" && (
            <MoonSwapPanel
              isYourTurn={isYourMoonSwapTurn}
              isBidder={isBidWinner}
              yourHand={state.your_hand}
              onSubmitSwapCard={sendSubmitMoonSwapCard}
            />
          )}

          {state.phase === "PLAYING" && isSittingOutPartner && (
            <div className="sitting-out-note">
              You're sitting out this hand -{" "}
              {playerName(state.winning_bid!.player_id, state.player_names)} is playing{" "}
              {bidLabel(state.winning_bid!.rung)} solo.
            </div>
          )}

          {!hideGenericHand && (
            <Hand
              cards={state.your_hand}
              yourTurn={state.phase === "PLAYING" && isYourPlayTurn}
              legalPlays={state.legal_plays}
              onPlay={sendPlayCard}
            />
          )}
        </>
      )}

      <Toast message={roundBannerMessage} onDismiss={roundBanner.dismiss} variant="info" />
      <Toast message={error} onDismiss={dismissError} variant="error" />
    </div>
  );
}
