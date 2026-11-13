/** Design thresholds are UI rules, not data values. */
export const PARTIAL_DATA_COVERAGE = 0.8; // IA §4: show "Partial data" below 80%.

/** Two-letter code for a pillar; the label carries the information, not the hue. */
export function pillarCode(id: string): string {
  return id.slice(0, 2).toUpperCase();
}
