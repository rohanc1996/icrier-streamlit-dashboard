/**
 * The site's data model.
 *
 * `data/derived/web/editions.json` is produced by `pipeline/export_editions.py`
 * through the CHIPS engine. Nothing here scores, re-weights or re-ranks a
 * country: this module filters, formats and lays out what the exporter built.
 */
import { scaleLinear, scaleLog } from 'd3';
import raw from '../data/editions.json';
import { FLAG_COUNT, editionsFlagIso3s, groupFlagIso3s, topByScoreIso3s } from './flags.mjs';
import { iso2For } from './iso.mjs';
import { formatComposite, formatPercent, formatRank, formatScore } from './format';
import type {
  CompositionChartModel,
  CompositionRowModel,
  FieldChartModel,
  FieldPointModel,
  ScatterChartModel,
  ScatterPointModel,
} from './overview-types';

/* ---------------------------------------------------------------- payload */

export interface CountryRow {
  iso3: string;
  country: string;
  shortName?: string;
  score: number | null;
  rank: number | null;
  coverage: number | null;
  indicatorsPresent: number | null;
  indicatorsTotal: number | null;
}

export interface CompositionPillar {
  id: string;
  weight: number;
  score: number | null;
  contribution: number | null;
}

export interface CompositionSourceRow {
  iso3: string;
  country: string;
  shortName?: string;
  rank: number;
  score: number;
  pillars: CompositionPillar[];
}

export interface VerdictPillarSource {
  id: string;
  of: number;
  points: Array<{ rank: number; xPct: number; dy: number }>;
  best: number | null;
  median: number | null;
  worst: number | null;
}

export interface VerdictCountry {
  iso3: string;
  country: string;
  shortName?: string;
  rank: number | null;
  score: number | null;
  pillars: Array<{ id: string; score: number | null; rank: number | null }>;
  best: { id: string; rank: number } | null;
  worst: { id: string; rank: number } | null;
}

export interface MethodBlock {
  field: {
    values: CountryRow[];
    median: number | null;
    min: number | null;
    max: number | null;
  };
  composition: CompositionSourceRow[];
  verdicts: {
    pillars: VerdictPillarSource[];
    countries: Record<string, VerdictCountry>;
  };
  sizeVsScore: Array<{
    iso3: string;
    country: string;
    shortName?: string;
    score: number;
    rank: number;
    gdp: number;
  }>;
  correlation: { pearson: number; spearman: number; n: number } | null;
}

export interface RobustnessRow {
  iso3: string;
  country: string;
  shortName?: string;
  rankFull: number;
  rankZ: number;
  delta: number;
}

export interface BasisBlock {
  year: string;
  basis: string;
  methods: Record<string, MethodBlock>;
  robustness: RobustnessRow[];
  countryCount: number;
  scoredCount: number;
}

export interface TrackerRow {
  iso3: string;
  country: string;
  shortName?: string;
  /** Rank per edition, keyed by year. No scores: not comparable across years. */
  ranks: Record<string, number>;
}

export interface TrackerBlock {
  window: string;
  years: number[];
  countries: TrackerRow[];
  count: number;
  note: string;
}

export interface DownloadLink {
  label: string;
  href: string;
  note: string;
}

export interface EditionsPayload {
  meta: {
    generated: string;
    years: string[];
    methods: string[];
    defaultMethod: string;
    defaults: { year: string; basis: string; group: string; compare: string[] };
    basisOrder: string[];
    basisAvailability: Record<string, string[]>;
    groups: Record<string, string[] | null>;
    groupLabels: Record<string, string>;
    editionCountryCount: Record<string, number>;
    gdpYear: string;
    leaves: number;
    edition: string;
  };
  editions: Record<string, Record<string, BasisBlock>>;
  tracker: Record<string, Record<string, TrackerBlock>>;
  downloads: DownloadLink[];
}

export const payload = raw as unknown as EditionsPayload;
export const meta = payload.meta;

/** Every country the latest edition carries, for the selectors. */
export const ALL_COUNTRIES = (() => {
  const block =
    payload.editions[meta.edition]?.[meta.defaults.basis] ??
    payload.editions[meta.edition]?.['absolute'];
  const rows = block?.methods[meta.defaultMethod]?.field.values ?? [];
  return rows
    .filter((row) => row.score !== null)
    .map((row) => ({ iso3: row.iso3, name: row.shortName || row.country }))
    .sort((a, b) => a.name.localeCompare(b.name, 'en'));
})();

/** The normalisation control is provisional. Set to false to hide it behind
 *  the "Advanced / methodology" disclosure without touching any other code. */
export const SHOW_NORMALIZATION_CONTROL = false;

export const METHODS = meta.methods;
export const DEFAULT_METHOD = meta.defaultMethod;
export const YEARS = meta.years;
export const BASIS_ORDER = meta.basisOrder;
export const BASIS_LABELS: Record<string, string> = {
  absolute: 'Absolute',
  relative: 'Relative',
  combined: 'Combined (50–50)',
};
export const GROUP_IDS = [
  'all',
  'g20',
  'g20em',
  'eu',
  'asean',
  'saarc',
  'au',
  'arab',
  'mercosur',
  'custom',
] as const;
export type GroupId = (typeof GROUP_IDS)[number];
export const GROUP_LABELS: Record<string, string> = {
  ...meta.groupLabels,
  custom: 'Custom selection',
};
export const METHOD_LABELS: Record<string, string> = {
  full_minmax: 'Min–max',
  z: 'Z-score',
};
export const DEFAULT_METHOD_LABEL = METHOD_LABELS[DEFAULT_METHOD] ?? DEFAULT_METHOD;

/**
 * Flags the build can actually draw: every country the editions carry, mapped
 * to alpha-2, because a grouping can flag any of its members. `scripts/
 * fetch-flags.mjs` vendors exactly this set, so a missing flag would be a
 * build-time error rather than a blank `<use>`.
 */
const VENDORED_FLAGS = new Set(
  editionsFlagIso3s(payload.editions)
    .map((iso3) => iso2For(iso3))
    .filter((iso2): iso2 is string => Boolean(iso2)),
);

export function flagFor(iso3: string): string | undefined {
  const iso2 = iso2For(iso3) ?? undefined;
  return iso2 && VENDORED_FLAGS.has(iso2) ? iso2 : undefined;
}

/** Union across every edition/basis/method, for the page sprite. */
export function allFlagIso2s(): string[] {
  return [...VENDORED_FLAGS].sort();
}

export function allPointIso3s(): string[] {
  const codes = new Set<string>();
  for (const bases of Object.values(payload.editions)) {
    for (const block of Object.values(bases)) {
      for (const method of Object.values(block.methods)) {
        for (const row of method.field.values) codes.add(row.iso3);
      }
    }
  }
  return [...codes].sort();
}

/* -------------------------------------------------------------- URL state */

export interface Filters {
  year: string;
  years: string[];
  basis: string;
  group: GroupId;
  custom: string[];
  compare: string[];
  method: string;
  pane: number;
}

export const DEFAULT_FILTERS: Filters = {
  year: meta.defaults.year,
  years: [meta.defaults.year],
  basis: meta.defaults.basis,
  group: meta.defaults.group as GroupId,
  custom: [],
  compare: meta.defaults.compare ?? [],
  method: meta.defaultMethod,
  pane: 1,
};

const PANE_COUNT = 7;

export function basisFor(year: string, requested: string): string {
  const available = meta.basisAvailability[year] ?? ['absolute'];
  return available.includes(requested) ? requested : available[0];
}

export function readFilters(search: string): Filters {
  const params = new URLSearchParams(search);
  const yearParam = params.get('year');
  const requestedYears = (yearParam ?? '')
    .split(',')
    .map((value) => value.trim())
    .filter((value) => YEARS.includes(value));
  const years = requestedYears.length ? [...new Set(requestedYears)].sort() : [DEFAULT_FILTERS.year];
  const year = years[years.length - 1];

  const groupParam = params.get('group') ?? DEFAULT_FILTERS.group;
  const group = (GROUP_IDS as readonly string[]).includes(groupParam)
    ? (groupParam as GroupId)
    : DEFAULT_FILTERS.group;

  const methodParam = params.get('scale');
  const method =
    methodParam === 'minmax'
      ? 'full_minmax'
      : methodParam === 'z'
        ? 'z'
        : DEFAULT_FILTERS.method;

  const compare = (params.get('compare') ?? '')
    .split(',')
    .map((value) => value.trim().toUpperCase())
    .filter((value) => /^[A-Z]{3}$/.test(value))
    .slice(0, 2);

  const custom = (params.get('countries') ?? '')
    .split(',')
    .map((value) => value.trim().toUpperCase())
    .filter((value) => /^[A-Z]{3}$/.test(value));

  const paneValue = Number(params.get('pane'));
  const pane =
    Number.isInteger(paneValue) && paneValue >= 1 && paneValue <= PANE_COUNT
      ? paneValue
      : 1;

  const basisParam = params.get('basis') ?? DEFAULT_FILTERS.basis;
  return {
    year,
    years,
    basis: basisFor(year, basisParam),
    group,
    custom,
    compare,
    method,
    pane,
  };
}

export function writeFilters(url: URL, filters: Filters): URL {
  const defaults = DEFAULT_FILTERS;
  const setOrDelete = (key: string, value: string, fallback: string) => {
    if (!value || value === fallback) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  };

  const years = [...filters.years].sort();
  setOrDelete('year', years.join(','), defaults.year);
  setOrDelete('basis', filters.basis, defaults.basis);
  setOrDelete('group', filters.group, defaults.group);
  setOrDelete('compare', filters.compare.join(','), defaults.compare.join(','));
  setOrDelete('countries', filters.custom.join(','), '');
  const token = filters.method === 'full_minmax' ? 'minmax' : 'z';
  const defaultToken = DEFAULT_FILTERS.method === 'full_minmax' ? 'minmax' : 'z';
  if (token === defaultToken) url.searchParams.delete('scale');
  else url.searchParams.set('scale', token);
  if (filters.pane === 1) url.searchParams.delete('pane');
  else url.searchParams.set('pane', String(filters.pane));
  return url;
}

export function selectionIso3s(filters: Filters): Set<string> | null {
  if (filters.group === 'custom') {
    return filters.custom.length ? new Set(filters.custom) : null;
  }
  const group = meta.groups[filters.group];
  return group ? new Set(group) : null;
}

/** The user-visible sentence describing the active view. */
export function selectionSummary(filters: Filters, methodLabel: string): string {
  const years = [...filters.years].sort().join(' and ');
  const group = GROUP_LABELS[filters.group] ?? filters.group;
  const compare = filters.compare.length === 2 ? ` · comparing ${filters.compare.join(' vs ')}` : '';
  return `${BASIS_LABELS[filters.basis] ?? filters.basis} scores · ${years} · ${group} · ${methodLabel}${compare}`;
}

/* ------------------------------------------------------------- primitives */

const DOT_RADIUS = 5;
const VIRTUAL_WIDTH = 1000;

function axisMax(values: number[]): number {
  const peak = values.length ? Math.max(...values.map((value) => value * 100)) : 0;
  return Math.max(70, Math.ceil(peak / 10) * 10);
}

function beeswarmPositions(values: number[], maxValue: number): Array<{ x: number; y: number }> {
  const gap = DOT_RADIUS * 2 + 1.5;
  const placed: Array<{ x: number; y: number }> = [];
  const positions = new Array<{ x: number; y: number }>(values.length);
  const order = values
    .map((value, index) => ({ value, index }))
    .sort((a, b) => a.value - b.value || a.index - b.index);
  for (const item of order) {
    const x0 = ((item.value * 100) / maxValue) * VIRTUAL_WIDTH;
    let spot = { x: x0, y: 0 };
    for (let attempt = 0; attempt < 2000; attempt += 1) {
      const angle = attempt * 2.399963;
      const radius = 0.5 * gap * Math.sqrt(attempt);
      const candidate = {
        x: x0 + radius * Math.cos(angle),
        y: radius * Math.sin(angle),
      };
      if (placed.every((point) => Math.hypot(point.x - candidate.x, point.y - candidate.y) >= gap)) {
        spot = candidate;
        break;
      }
    }
    positions[item.index] = spot;
    placed.push(spot);
  }
  return positions;
}

/* ---------------------------------------------------------- pane 1 field */

export function buildFieldModel(method: MethodBlock, selected: Set<string> | null): FieldChartModel {
  const source = method.field.values.filter((row) => row.score !== null);
  const max = axisMax(source.map((row) => row.score as number));
  const x = scaleLinear().domain([0, max]).range([3, 97]);
  const positions = beeswarmPositions(source.map((row) => row.score as number), max);
  const top = Math.min(...positions.map((spot) => spot.y));
  const bottom = Math.max(...positions.map((spot) => spot.y));
  const plotTop = 24;
  const centre = plotTop + Math.abs(top) + DOT_RADIUS + 10;
  const axisY = centre + bottom + DOT_RADIUS + 22;
  const height = axisY + 30;
  const flagRows = source.map((row) => ({
    iso3: row.iso3,
    score: row.score as number,
    rank: row.rank as number,
  }));
  const topFlags = selected
    ? groupFlagIso3s(flagRows, selected)
    : topByScoreIso3s(flagRows, FLAG_COUNT);

  const points: FieldPointModel[] = source.map((row, index) => {
    const spot = positions[index];
    const flagRank = topFlags.indexOf(row.iso3) + 1 || undefined;
    const flagIso2 = flagRank ? flagFor(row.iso3) : undefined;
    return {
      iso3: row.iso3,
      label: row.shortName || row.country,
      score: row.score as number,
      rank: row.rank ?? 0,
      xPct: x((spot.x / VIRTUAL_WIDTH) * max),
      cy: centre + spot.y,
      isIndia: row.iso3 === 'IND',
      flagRank: flagIso2 ? flagRank : undefined,
      flagIso2,
      inSelection: selected ? selected.has(row.iso3) : true,
    } as FieldPointModel;
  });

  const median = method.field.median ?? 0;
  return {
    kind: 'field',
    points,
    medianPct: x(median * 100),
    medianLabel: formatComposite(median),
    height,
    axisY,
    ticks: Array.from({ length: max / 10 + 1 }, (_, index) => ({
      pct: x(index * 10),
      label: String(index * 10),
    })),
    ariaLabel:
      `Beeswarm of ${points.length} CHIPS scores from ${formatComposite(method.field.min ?? 0)} ` +
      `to ${formatComposite(method.field.max ?? 0)}, median ${formatComposite(median)}.`,
  };
}

/* ----------------------------------------------------- pane 2 rank bars */

export interface RankBarRow {
  iso3: string;
  label: string;
  score: number;
  scoreText: string;
  rank: number;
  pct: number;
}

export function buildRankBars(method: MethodBlock): { rows: RankBarRow[]; max: number } {
  const source = method.field.values.filter(
    (row): row is CountryRow & { score: number; rank: number } =>
      row.score !== null && row.rank !== null,
  );
  const max = axisMax(source.map((row) => row.score));
  const x = scaleLinear().domain([0, max]).range([0, 100]);
  return {
    max,
    rows: source.map((row) => ({
      iso3: row.iso3,
      label: row.shortName || row.country,
      score: row.score,
      scoreText: formatComposite(row.score),
      rank: row.rank,
      pct: x(row.score * 100),
    })),
  };
}

/* ------------------------------------------------ pane 3 composition */

export function buildCompositionModel(method: MethodBlock): CompositionChartModel {
  const source = method.composition;
  const peak = Math.max(...source.map((row) => row.score));
  const max = Math.max(10, Math.ceil((peak * 100) / 10) * 10);
  const x = scaleLinear().domain([0, max]).range([0, 100]);
  const pillarOrder = method.verdicts.pillars.map((pillar) => pillar.id);
  const rows: CompositionRowModel[] = source.map((row) => {
    let cursor = 0;
    const segments = pillarOrder.map((id) => {
      const pillar = row.pillars.find((item) => item.id === id);
      const contribution = pillar?.contribution ?? 0;
      const widthPct = x(contribution * 100);
      const segment = {
        id,
        contribution,
        startPct: cursor,
        widthPct,
        text: formatComposite(contribution),
      };
      cursor += widthPct;
      return segment;
    });
    return {
      iso3: row.iso3,
      label: row.shortName || row.country,
      rank: row.rank,
      total: row.score,
      totalText: formatComposite(row.score),
      segments,
    };
  });
  const weights = source[0]?.pillars ?? [];
  return {
    kind: 'composition',
    rows,
    pillarOrder,
    legend: pillarOrder.map((id) => {
      const weight = weights.find((pillar) => pillar.id === id)?.weight;
      return {
        id,
        label: id,
        weightText: weight === undefined ? '' : formatPercent(weight, 1),
      };
    }),
    ticks: Array.from({ length: max / 10 + 1 }, (_, index) => ({
      pct: x(index * 10),
      label: String(index * 10),
    })),
    ariaLabel: `Stacked bars of the weighted pillar contributions for ${rows.length} countries.`,
  };
}

/* --------------------------------------------------- panes 4 verdicts */

export interface VerdictMark {
  id: string;
  scoreText: string;
  rank: number;
  of: number;
  xPct: number;
  points: Array<{ rank: number; xPct: number; dy: number }>;
  best: number;
  median: number;
  worst: number;
}

export function buildVerdictMarks(
  method: MethodBlock,
  iso3: string,
): { country: string; marks: VerdictMark[]; best: { id: string; rank: number } | null; worst: { id: string; rank: number } | null } | null {
  const country = method.verdicts.countries[iso3];
  if (!country) return null;
  const marks = method.verdicts.pillars.flatMap((pillar) => {
    const value = country.pillars.find((item) => item.id === pillar.id);
    if (!value || value.rank === null) return [];
    const total = pillar.of;
    return [{
      id: pillar.id,
      scoreText: value.score === null ? '—' : formatScore(value.score),
      rank: value.rank,
      of: total,
      xPct: total > 1 ? 3 + ((value.rank - 1) / (total - 1)) * 94 : 50,
      points: pillar.points,
      best: pillar.best ?? 1,
      median: pillar.median ?? total / 2,
      worst: pillar.worst ?? total,
    }];
  });
  return {
    country: country.country,
    marks,
    best: country.best,
    worst: country.worst,
  };
}

/* ---------------------------------------------------- pane 5 tracker */

export function trackerBlock(method: string, years: string[]): TrackerBlock | null {
  const key = [...years].sort().join(',');
  return payload.tracker[method]?.[key] ?? null;
}

/* ------------------------------------------------- pane 6 robustness */

export function robustnessRows(filters: Filters): RobustnessRow[] {
  const block = payload.editions[filters.year]?.[filters.basis];
  return block?.robustness ?? [];
}

/* ------------------------------------------------------ pane 7 scatter */

const SCATTER_HEIGHT = 360;
const SCATTER_TOP = 18;
const SCATTER_BOTTOM = 306;
const SCATTER_LEFT_PCT = 10;
const SCATTER_RIGHT_PCT = 96;

function scoreAxisMax(scores: number[]): number {
  const peak = scores.length ? Math.max(...scores) * 100 : 0;
  return Math.max(50, Math.ceil(peak / 10) * 10);
}

function formatUsd(value: number): string {
  const scale = value >= 1e12 ? { divisor: 1e12, suffix: 'tn' } : { divisor: 1e9, suffix: 'bn' };
  const scaled = value / scale.divisor;
  const digits = scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2;
  return `$${Number(scaled.toFixed(digits))}${scale.suffix}`;
}

export function buildSizeScatter(method: MethodBlock, selected: Set<string> | null): ScatterChartModel | null {
  const source = method.sizeVsScore.filter((row) => Number.isFinite(row.gdp) && row.gdp > 0);
  if (!source.length) return null;
  const gdp = source.map((row) => row.gdp);
  const min = Math.min(...gdp);
  const max = Math.max(...gdp);
  const x = scaleLog().domain([min / 1.2, max * 1.6]).range([SCATTER_LEFT_PCT, SCATTER_RIGHT_PCT]);
  const yMax = scoreAxisMax(source.map((row) => row.score));
  const y = scaleLinear().domain([0, yMax]).range([SCATTER_BOTTOM, SCATTER_TOP]);
  const flagRows = source.map((row) => ({
    iso3: row.iso3,
    score: row.score,
    rank: row.rank,
  }));
  const topFlags = selected
    ? groupFlagIso3s(flagRows, selected)
    : topByScoreIso3s(flagRows, FLAG_COUNT);
  const labelled = new Set(['USA', 'CHN', 'IND']);
  const smaller = [...source]
    .filter((row) => row.gdp < 1e12 && !labelled.has(row.iso3))
    .sort((a, b) => b.score - a.score || a.country.localeCompare(b.country))[0];
  if (smaller) labelled.add(smaller.iso3);

  const points: ScatterPointModel[] = source.map((row) => {
    const flagRank = topFlags.indexOf(row.iso3) + 1 || undefined;
    const flagIso2 = flagRank ? flagFor(row.iso3) : undefined;
    const xPct = x(row.gdp);
    return {
      iso3: row.iso3,
      label: row.iso3 === 'USA' ? 'United States' : row.shortName || row.country,
      score: row.score,
      gdp: row.gdp,
      xPct,
      y: y(row.score * 100),
      flagRank: flagIso2 ? flagRank : undefined,
      flagIso2,
      labelXPct: labelled.has(row.iso3) ? xPct : undefined,
      labelY: labelled.has(row.iso3) ? y(row.score * 100) - 11 : undefined,
      labelAnchor: xPct > 88 ? 'end' : xPct < 14 ? 'start' : 'middle',
      inSelection: selected ? selected.has(row.iso3) : true,
    } as ScatterPointModel;
  });

  const tickValues = [5e10, 5e11, 5e12, 3e13].filter(
    (value) => value >= min / 1.2 && value <= max * 1.6,
  );

  return {
    kind: 'sizeScore',
    points,
    xTicks: tickValues.map((value) => ({ pct: x(value), label: formatUsd(value) })),
    yTicks: Array.from({ length: yMax / 10 + 1 }, (_, index) => ({
      y: y(index * 10),
      label: String(index * 10),
    })),
    height: SCATTER_HEIGHT,
    plotLeftPct: SCATTER_LEFT_PCT,
    plotRightPct: SCATTER_RIGHT_PCT,
    ariaLabel:
      `Scatter of GDP ${meta.gdpYear} on a logarithmic axis against the CHIPS score, ` +
      `${points.length} countries.`,
  };
}

/* ---------------------------------------------------------- table models */

export interface TableModel {
  caption: string;
  columns: string[];
  rows: string[][];
  note: string;
  numericColumns?: number[];
}

export function rankBarTable(rows: RankBarRow[], groupLabel: string): TableModel {
  return {
    caption: `${rows.length} ${groupLabel.toLowerCase()} ranked by CHIPS score.`,
    columns: ['Rank', 'Country', 'CHIPS score'],
    numericColumns: [0, 2],
    rows: rows.map((row) => [formatRank(row.rank), row.label, row.scoreText]),
    note: 'Ranks are positions in the published field, not within the selected group.',
  };
}

export function compositionTable(model: CompositionChartModel): TableModel {
  return {
    caption: `Pillar contributions for ${model.rows.length} countries.`,
    columns: ['Rank', 'Country', 'Pillar', 'Contribution', 'Score'],
    numericColumns: [0, 3, 4],
    rows: model.rows.flatMap((row) =>
      row.segments.map((segment) => [
        formatRank(row.rank),
        row.label,
        segment.id,
        segment.text,
        row.totalText,
      ]),
    ),
    note: 'Contribution is pillar score × effective weight on the 0–100 scale; the five sum to the score.',
  };
}

export function verdictTable(
  marks: VerdictMark[],
  country: string,
  overallRank: number | null,
): TableModel {
  return {
    caption: `${country}'s rank in each pillar.`,
    columns: ['Pillar', 'Score', 'Rank', 'Of'],
    numericColumns: [1, 2, 3],
    rows: marks.map((mark) => [mark.id, mark.scoreText, formatRank(mark.rank), formatRank(mark.of)]),
    note: `Pillar ranks are within the pillar, not the overall rank${
      overallRank === null ? '' : ` (${formatRank(overallRank)} overall)`
    }.`,
  };
}

export function sizeTable(method: MethodBlock): TableModel {
  const rows = [...method.sizeVsScore].sort((a, b) => a.rank - b.rank);
  return {
    caption: `CHIPS score and GDP ${meta.gdpYear} for ${rows.length} countries.`,
    columns: ['Rank', 'Country', 'CHIPS score', `GDP ${meta.gdpYear}`],
    numericColumns: [0, 2, 3],
    rows: rows.map((row) => [
      formatRank(row.rank),
      row.shortName || row.country,
      formatComposite(row.score),
      formatUsd(row.gdp),
    ]),
    note: 'GDP is current US dollars, joined by ISO-3. The Absolute edition scores volumes, so size and score are partly related by construction.',
  };
}
