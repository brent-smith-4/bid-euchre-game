// Plain content, no modal chrome of its own, so it can be dropped into the
// landing page's How to Play modal AND (later) a shorter in-game reference
// without duplicating the rules text in two places.
export function RulesContent() {
  return (
    <div className="rules-content">
      <section>
        <h3>Object</h3>
        <p>
          4 players in 2 fixed partnerships (partners sit across from each other) race to a target
          score by bidding on, then winning, tricks.
        </p>
      </section>

      <section>
        <h3>The deal</h3>
        <p>
          A single 24-card deck (9 through Ace). Each player gets 6 cards; 6 tricks are played
          each hand.
        </p>
      </section>

      <section>
        <h3>Bidding</h3>
        <p>
          Starting left of the dealer, each player passes or bids up the ladder:{" "}
          <strong>3 &rarr; 4 &rarr; 5 &rarr; 6 &rarr; Shoot the Moon &rarr; Go Alone</strong>. A
          bid just has to beat the current high bid - jumping rungs is fine. If everyone before
          the dealer passes, the dealer is stuck and must bid at least 3.
        </p>
      </section>

      <section>
        <h3>Calling trump</h3>
        <p>
          Whoever wins the bid calls trump: any suit, or no-trump <strong>High</strong> (Ace high
          down to 9 low) or <strong>Low</strong> (9 high down to Ace low).
        </p>
      </section>

      <section>
        <h3>Card ranking</h3>
        <p>
          With a suit as trump: right bower (jack of trump) beats left bower (jack of the
          same-color suit), then Ace, King, Queen, 10, 9. No-trump High: Ace down to 9. No-trump
          Low: 9 down to Ace.
        </p>
      </section>

      <section>
        <h3>Playing a trick</h3>
        <p>
          The player left of the dealer leads first. Follow suit if you can; otherwise trump in
          or discard. Highest card of the suit led wins, unless someone trumped in - then highest
          trump wins. The trick winner leads next.
        </p>
      </section>

      <section>
        <h3>Scoring</h3>
        <ul>
          <li>
            <strong>3-6 bid:</strong> make it (take at least that many tricks) and everyone scores
            1 point per trick they won, bidder included. Fall short and the bidding team is "set"
            - they lose points equal to their bid, while the other team still scores their tricks.
          </li>
          <li>
            <strong>Shoot the Moon (worth 12, or -12 if set):</strong> commit to winning all 6
            tricks solo. Your partner sits out the hand, but first swaps you one hidden card,
            blind, for your weakest.
          </li>
          <li>
            <strong>Go Alone (worth 24, or -24 if set):</strong> same commitment as Moon, but no
            card swap - and double the points.
          </li>
        </ul>
      </section>
    </div>
  );
}
