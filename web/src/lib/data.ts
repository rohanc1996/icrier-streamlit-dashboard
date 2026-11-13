import raw from '../data/2026/chips.json';
import type { ChipsData, IndicatorRow, Pillar, ScoreRow } from './types';
import { methodLabel } from './scale';

/**
 * Contract v2: chips.json carries one payload per scaling method under
 * `methods{}`. Nothing below assumes which method produced a number.
 */
const chips = raw as unknown as ChipsData;

export const meta = chips.meta;
export const pillars: Pillar[] = chips.framework.pillars;

export const scaleIds: string[] =
  Array.isArray(meta.methods) && meta.methods.length > 0
    ? meta.methods
    : Object.keys(chips.methods);

export const defaultScale: string =
  meta.defaultMethod && scaleIds.includes(meta.defaultMethod)
    ? meta.defaultMethod
    : scaleIds[0];

export interface ScaleData {
  id: string;
  scores: ScoreRow[];
  indicators: IndicatorRow[];
  /**
   * Denominator for the "r of N" label, per sub-pillar: the number of
   * countries where the exporter marked the sub-pillar present. The rank
   * itself is read from `scores[].subPillars[key].rank`; it is never derived
   * here.
   */
  subPillarOf: Record<string, number>;
  median: number;
  min: number;
  max: number;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

/**
 * Counts, not ranks. The exporter now carries every sub-pillar's `rank`, so
 * this function only supplies the "of N" denominator used beside it. It does
 * not round, sort or compare scores.
 */
function countScoredSubPillars(scores: ScoreRow[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const row of scores) {
    for (const [key, item] of Object.entries(row.subPillars)) {
      if (item.status === 'present' && item.score !== null) {
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
  }
  return counts;
}

function buildScale(id: string): ScaleData {
  const payload = chips.methods[id];
  if (!payload) throw new Error(`chips.json has no methods['${id}'] payload`);
  const scores = [...payload.scores].sort((a, b) => a.rank - b.rank);
  const overalls = scores.map((row) => row.overall);
  return {
    id,
    scores,
    indicators: payload.indicators,
    subPillarOf: countScoredSubPillars(scores),
    median: median(overalls),
    min: Math.min(...overalls),
    max: Math.max(...overalls),
  };
}

export const scales: Record<string, ScaleData> = Object.fromEntries(
  scaleIds.map((id) => [id, buildScale(id)]),
);

export const defaultData: ScaleData = scales[defaultScale];

export function getScaleData(id: string | null | undefined): ScaleData {
  return (id && scales[id]) || defaultData;
}

/** Build-time country list used by the header search. */
export const countries = defaultData.scores
  .map((row) => ({
    iso3: row.iso3,
    name: row.shortName || row.country,
    fullName: row.country,
  }))
  .sort((a, b) => a.name.localeCompare(b.name, 'en'));

/** Countries whose coverage is complete, computed rather than hard-coded. */
export function fullCoverageCount(data: ScaleData): number {
  return data.scores.filter((row) => row.coverage >= 0.9999).length;
}

/**
 * The movement column is always measured against min–max when that method is
 * present, regardless of which method is the build default.
 */
export const baselineScale: string = scaleIds.includes('full_minmax')
  ? 'full_minmax'
  : defaultScale;

export const comparisonScale: string | null =
  scaleIds.find((id) => id !== baselineScale) ?? null;

export interface MethodComparison {
  available: boolean;
  baselineId: string;
  otherId: string | null;
  otherLabel: string;
  differing: number;
  countryCount: number;
  indicatorComparable: number;
  indicatorDiffering: number;
  max: { iso3: string; name: string; from: number; to: number; delta: number } | null;
}

/**
 * Composite ranks are a weighted sum, so a monotone change to each indicator
 * can still reorder the total. Measure both levels from the data and let the
 * page state the result instead of a slogan.
 */
export const methodComparison: MethodComparison = (() => {
  if (!comparisonScale) {
    return {
      available: false,
      baselineId: baselineScale,
      otherId: null,
      otherLabel: '',
      differing: 0,
      countryCount: scales[baselineScale].scores.length,
      indicatorComparable: 0,
      indicatorDiffering: 0,
      max: null,
    };
  }

  const baseline = new Map(scales[baselineScale].scores.map((row) => [row.iso3, row]));
  let differing = 0;
  let max: MethodComparison['max'] = null;

  for (const row of scales[comparisonScale].scores) {
    const before = baseline.get(row.iso3);
    if (!before) continue;
    const delta = before.rank - row.rank;
    if (Math.abs(delta) > 1e-9) {
      differing += 1;
      if (!max || Math.abs(delta) > Math.abs(max.delta)) {
        max = {
          iso3: row.iso3,
          name: row.shortName || row.country,
          from: before.rank,
          to: row.rank,
          delta,
        };
      }
    }
  }

  const baselineIndicators = new Map(
    scales[baselineScale].indicators.map((row) => [`${row.iso3}|${row.leaf}`, row]),
  );
  let indicatorComparable = 0;
  let indicatorDiffering = 0;
  for (const row of scales[comparisonScale].indicators) {
    const before = baselineIndicators.get(`${row.iso3}|${row.leaf}`);
    if (!before || before.rank === null || row.rank === null) continue;
    indicatorComparable += 1;
    if (Math.abs(before.rank - row.rank) > 1e-9) indicatorDiffering += 1;
  }

  return {
    available: true,
    baselineId: baselineScale,
    otherId: comparisonScale,
    otherLabel: methodLabel(comparisonScale),
    differing,
    countryCount: scales[comparisonScale].scores.length,
    indicatorComparable,
    indicatorDiffering,
    max,
  };
})();

/** Total sub-pillars in the framework, used in coverage lines. */
export const subPillarCount = pillars.reduce(
  (total, pillar) => total + pillar.subPillars.length,
  0,
);

export function notScoredSubPillars(row: ScoreRow): number {
  return Object.values(row.subPillars).filter((item) => item.status !== 'present').length;
}

export function indicatorCount(pillar: Pillar): number {
  return pillar.subPillars.reduce((total, sub) => total + sub.leaves.length, 0);
}
