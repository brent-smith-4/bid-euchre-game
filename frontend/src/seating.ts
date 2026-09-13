export type TablePosition = "bottom" | "left" | "top" | "right";

const POSITIONS: TablePosition[] = ["bottom", "left", "top", "right"];

// Rotates the fixed 4-seat table (per NUM_PLAYERS/team_of in models.py -
// seats 0&2 and 1&3 are partners, turn order is clockwise by seat id) so
// the viewer always renders at "bottom", matching the existing clockwise
// order: +1 = left, +2 = partner (top), +3 = right.
export function relativeSeat(yourId: number, seatId: number): TablePosition {
  const offset = (seatId - yourId + 4) % 4;
  return POSITIONS[offset];
}
