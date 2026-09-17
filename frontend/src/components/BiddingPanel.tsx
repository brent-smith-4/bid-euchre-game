import { BID_LADDER, bidDescription, bidLabel } from "../protocol";
import type { BidRung } from "../protocol";

interface BiddingPanelProps {
  yourTurn: boolean;
  legalBids: BidRung[];
  onBid: (rung: BidRung) => void;
  // Defaults match a Normal-length game (see room.GAME_LENGTHS) - GameRoom
  // always passes the server's actual state.moon_points/alone_points, since
  // the current match's game length decides these, not this component.
  moonPoints?: number;
  alonePoints?: number;
}

// Buttons map straight to the server-provided legal_bids (GameSession.legal_bids,
// which reuses is_legal_bid) rather than reimplementing the bid ladder here -
// per the bidding-ui-and-timeouts decision. No timers: deferred by design.
export function BiddingPanel({
  yourTurn,
  legalBids,
  onBid,
  moonPoints = 12,
  alonePoints = 24,
}: BiddingPanelProps) {
  if (!yourTurn) {
    return <div className="bidding-panel waiting">Waiting for the other bidders...</div>;
  }

  const pointValue: Partial<Record<BidRung, string>> = {
    MOON: `${moonPoints} pts`,
    ALONE: `${alonePoints} pts`,
  };

  return (
    <div className="bidding-panel">
      <p>
        <strong>Your Bid:</strong> # of tricks you think your team can take
      </p>
      <div className="bid-buttons">
        {BID_LADDER.map((rung) => (
          <button
            key={rung}
            type="button"
            disabled={!legalBids.includes(rung)}
            onClick={() => onBid(rung)}
            title={bidDescription(rung)}
          >
            {bidLabel(rung)}
            {pointValue[rung] && <span className="bid-points">{pointValue[rung]}</span>}
          </button>
        ))}
      </div>
      <p className="bid-legend">
        <strong>Shoot the Moon</strong>: 6 tricks solo, partner card swap
        <br />
        <strong>Go Alone</strong>: 6 tricks solo
      </p>
    </div>
  );
}
