interface CardBackProps {
  size?: "normal" | "mini";
}

// A face-down card - used for teammates'/opponents' on-table hand display
// (see Seat.tsx) and as the flying sprites in the deal animation (see
// useDealAnimation.ts). Never interactive: nobody but the server (and the
// card's own owner, via their own face-up hand) knows what it actually is.
export function CardBack({ size = "normal" }: CardBackProps) {
  return <div className={`card-back${size === "mini" ? " card-back-mini" : ""}`} aria-hidden="true" />;
}
