import { BID_LADDER, bidDescription, bidLabel } from "../protocol";
import type { BidRung } from "../protocol";

const POINT_VALUE: Partial<Record<BidRung, string>> = { MOON: "12 pts", ALONE: "24 pts" };

interface BiddingPanelProps {
  yourTurn: boolean;
  legalBids: BidRung[];
  onBid: (rung: BidRung) => void;
}

// Buttons map straight to the server-provided legal_bids (GameSession.legal_bids,
// which reuses is_legal_bid) rather than reimplementing the bid ladder here -
// per the bidding-ui-and-timeouts decision. No timers: deferred by design.
export function BiddingPanel({ yourTurn, legalBids, onBid }: BiddingPanelProps) {
  if (!yourTurn) {
    return <div className="bidding-panel waiting">Waiting for the other bidders...</div>;
  }

  return (
    <div className="bidding-panel">
      <p>Your bid: bid the number of tricks (3-6) you and your partner will take, or go bigger.</p>
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
            {POINT_VALUE[rung] && <span className="bid-points">{POINT_VALUE[rung]}</span>}
          </button>
        ))}
      </div>
      <p className="bid-legend">
        <strong>Shoot the Moon</strong>: all 6 tricks, partner card swap. <strong>Go Alone</strong>: all 6
        tricks solo, partner sits out.
      </p>
    </div>
  );
}
