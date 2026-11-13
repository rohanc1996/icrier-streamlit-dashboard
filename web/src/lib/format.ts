/**
 * One place converts the 0–1 export scale to the 0–100 display scale.
 * Components receive 0–1 values and never multiply by 100 themselves.
 */
export function to100(fraction: number): number {
  return fraction * 100;
}

export function clamp(value: number, min = 0, max = 100): number {
  return Math.min(max, Math.max(min, value));
}

/** Indicator and pillar scores: 1 decimal, per the display rule. */
export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return to100(value).toFixed(1);
}

/**
 * The final CHIPS composite: 2 decimals. AGENTS invariant 5 and IA §5.2 both
 * round the composite on the 0–100 scale to 2 dp; 1 dp hides ties that sit at
 * different ranks.
 */
export function formatComposite(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return to100(value).toFixed(2);
}

export function formatRank(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  // Ranks come from the exporter; never round them in the frontend.
  return String(value);
}

/** Weights and coverage are fractions too; keep 1 decimal at most. */
export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const rounded = Number(to100(value).toFixed(digits));
  return `${rounded}%`;
}

export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export function plural(count: number, singular: string, pluralForm?: string): string {
  return count === 1 ? singular : (pluralForm ?? `${singular}s`);
}
