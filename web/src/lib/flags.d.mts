/** Types for the flag-set rules in `flags.mjs`. */

export interface FlagCandidate {
  iso3: string;
  score: number;
  rank: number;
}

export const FLAG_COUNT: number;
export const TOP15_COUNT: number;

export function topByScoreIso3s(
  values: readonly FlagCandidate[] | null | undefined,
  count: number,
): string[];

export function methodFlagIso3s(
  fieldValues: readonly FlagCandidate[] | null | undefined,
  top15Rows: ReadonlyArray<{ iso3: string }> | null | undefined,
): string[];

export function pageFlagIso3s(
  methods: Record<string, { field?: { values?: readonly FlagCandidate[] }; top15?: Array<{ iso3: string }> }> | null | undefined,
): string[];
