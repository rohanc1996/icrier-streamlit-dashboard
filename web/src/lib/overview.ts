/**
 * Build-time model for the overview carousel.
 *
 * The data agent publishes `data/derived/web/overview.json`; this module uses
 * it when it is present and derives the two built panes from chips.json when
 * it is not. Nothing here runs in the browser: geometry is computed once at
 * build time and passed to the island as plain numbers.
 */
import { scaleLinear, scaleLog } from 'd3';
import rawSeries from '../data/series.json';
import {
  defaultData,
  defaultScale,
  meta,
  methodComparison,
  notScoredSubPillars,
  pillars,
  scaleIds,
  scales,
} from './data';
import { formatComposite, formatPercent, formatRank } from './format';
import { movementRuns } from './movement.mjs';
import { methodShortLabel } from './scale';
import type {
  CompositionChartModel,
  FieldChartModel,
  FieldPointModel,
  IndiaChartModel,
  MovementChartModel,
  MovementPointModel,
  MovementRowModel,
  OverviewCorrelationJson,
  OverviewJson,
  OverviewMethodJson,
  OverviewView,
  PaneModel,
  PaneTableModel,
  ScaleMovementChartModel,
  ScatterChartModel,
  ScatterPointModel,
  Top15ChartModel,
  Top15RowModel,
  VerdictPointModel,
} from './overview-types';

/**
 * `overview.json` is produced in parallel with this wave, so it is loaded
 * through Vite's glob: no match means `{}` and the build still succeeds.
 */
const overviewFiles = import.meta.glob<OverviewJson>('../data/overview.json', {
  eager: true,
  import: 'default',
});

const overview: OverviewJson | null =
  Object.values(overviewFiles)[0] ?? null;

const DOT_RADIUS = 5;
// A virtual plot width keeps the build-time placement stable between a
// desktop and a narrow screen; the marks themselves are positioned in
// percentages, so the swarm compresses instead of scrolling.
const VIRTUAL_WIDTH = 1000;

const countryLabel = (row: { shortName?: string; country: string }): string =>
  row.shortName || row.country;

/**
 * Chart labels for the handful of points pane 7 names. The full exporter name
 * ("United States of America") is too long for a scatter label; the table keeps
 * the full name.
 */
const SHORT_CHART_NAMES: Record<string, string> = { USA: 'United States' };

/** One decimal place is the indicator/pillar rule; composites keep two. */
const scoreText = (value: number): string => formatComposite(value);

function axisMax(values: number[]): number {
  const peak = values.length ? Math.max(...values.map((value) => value * 100)) : 0;
  return Math.max(70, Math.ceil(peak / 10) * 10);
}

/**
 * Deterministic build-time beeswarm. Each dot starts at its score's x and
 * searches a golden-angle spiral for the nearest spot that does not collide
 * with an already-placed dot, so dense clusters spread sideways and upwards
 * instead of stacking into a single tall column.
 */
function beeswarmPositions(
  values: number[],
  maxValue: number,
): Array<{ x: number; y: number }> {
  const gap = DOT_RADIUS * 2 + 1.5;
  const placed: Array<{ x: number; y: number }> = [];
  const positions = new Array<{ x: number; y: number }>(values.length);
  const order = values
    .map((value, index) => ({ value, index }))
    .sort((a, b) => a.value - b.value || a.index - b.index);

  for (const item of order) {
    // `value` is 0–1 and `maxValue` is on the 0–100 display scale.
    const x0 = ((item.value * 100) / maxValue) * VIRTUAL_WIDTH;
    let spot = { x: x0, y: 0 };

    for (let attempt = 0; attempt < 2000; attempt += 1) {
      const angle = attempt * 2.399963; // golden angle
      const radius = 0.5 * gap * Math.sqrt(attempt);
      const candidate = {
        x: x0 + radius * Math.cos(angle),
        y: radius * Math.sin(angle),
      };
      const clear = placed.every(
        (point) => Math.hypot(point.x - candidate.x, point.y - candidate.y) >= gap,
      );
      if (clear) {
        spot = candidate;
        break;
      }
    }

    positions[item.index] = spot;
    placed.push(spot);
  }

  return positions;
}

interface FieldSource {
  values: Array<{ iso3: string; country: string; shortName?: string; score: number; rank: number }>;
  median: number;
  min: number;
  max: number;
}

function methodBlock(id: string): OverviewMethodJson | null {
  return overview?.methods?.[id] ?? null;
}

function fieldSource(id: string): FieldSource {
  const block = methodBlock(id);
  if (block?.field?.values?.length) {
    return block.field;
  }
  const fallback = scales[id] ?? defaultData;
  return {
    values: fallback.scores.map((row) => ({
      iso3: row.iso3,
      country: row.country,
      shortName: row.shortName,
      score: row.overall,
      rank: row.rank,
    })),
    median: fallback.median,
    min: fallback.min,
    max: fallback.max,
  };
}

function buildFieldChart(source: FieldSource): FieldChartModel {
  const max = axisMax(source.values.map((row) => row.score));
  // Inset the range so the first and last tick labels are never clipped.
  const x = scaleLinear().domain([0, max]).range([3, 97]);
  const positions = beeswarmPositions(
    source.values.map((row) => row.score),
    max,
  );

  const top = Math.min(...positions.map((spot) => spot.y));
  const bottom = Math.max(...positions.map((spot) => spot.y));
  const plotTop = 24;
  const centre = plotTop + Math.abs(top) + DOT_RADIUS + 10;
  const axisY = centre + bottom + DOT_RADIUS + 22;
  const height = axisY + 30;

  const points: FieldPointModel[] = source.values.map((row, index) => {
    const spot = positions[index];
    return {
      iso3: row.iso3,
      label: countryLabel(row),
      score: row.score,
      rank: row.rank,
      xPct: x((spot.x / VIRTUAL_WIDTH) * max),
      cy: centre + spot.y,
      isIndia: row.iso3 === 'IND',
    };
  });

  const india = points.find((point) => point.isIndia);
  const ticks = Array.from({ length: max / 10 + 1 }, (_, index) => ({
    pct: x(index * 10),
    label: String(index * 10),
  }));

  return {
    kind: 'field',
    points,
    medianPct: x(source.median * 100),
    medianLabel: scoreText(source.median),
    height,
    axisY,
    ticks,
    ariaLabel:
      `Beeswarm of ${points.length} CHIPS scores, from ${scoreText(source.min)} to ` +
      `${scoreText(source.max)}, with the median at ${scoreText(source.median)}.` +
      (india ? ` India is ${ordinal(india.rank)} with ${scoreText(india.score)}.` : ''),
  };
}

function ordinal(value: number): string {
  const rest = value % 100;
  if (rest >= 11 && rest <= 13) return `${value}th`;
  const suffix = value % 10 === 1 ? 'st' : value % 10 === 2 ? 'nd' : value % 10 === 3 ? 'rd' : 'th';
  return `${value}${suffix}`;
}

interface Top15Source {
  iso3: string;
  country: string;
  shortName?: string;
  score: number;
  rank: number;
}

function top15Source(id: string): Top15Source[] {
  const block = methodBlock(id);
  if (block?.top15?.length) {
    return [...block.top15].sort((a, b) => a.rank - b.rank).slice(0, 15);
  }
  return [...(scales[id] ?? defaultData).scores]
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 15)
    .map((row) => ({
      iso3: row.iso3,
      country: row.country,
      shortName: row.shortName,
      score: row.overall,
      rank: row.rank,
    }));
}

function buildTop15Chart(rows: Top15Source[], max: number): Top15ChartModel {
  const x = scaleLinear().domain([0, max]).range([0, 100]);
  const models: Top15RowModel[] = rows.map((row) => ({
    iso3: row.iso3,
    label: countryLabel(row),
    score: row.score,
    rank: row.rank,
    pct: x(row.score * 100),
    scoreText: scoreText(row.score),
    isTop3: row.rank <= 3,
  }));

  // The pack below the podium: places 4–13. Read, never hard-coded.
  const from = models[3];
  const to = models[12];

  return {
    kind: 'top15',
    rows: models,
    spanFrom: from ? from.scoreText : '—',
    spanTo: to ? to.scoreText : '—',
    ariaLabel:
      `Lollipop of the top 15 CHIPS scores. ${models
        .slice(0, 3)
        .map((row) => `${row.label} ${row.scoreText}`)
        .join(', ')} lead the field.`,
  };
}

function fieldTable(source: FieldSource): PaneTableModel {
  const rows = [...source.values]
    .sort((a, b) => a.rank - b.rank)
    .map((row) => [
      formatRank(row.rank),
      countryLabel(row),
      scoreText(row.score),
    ]);
  return {
    caption: `All ${rows.length} CHIPS scores, highest ranked first.`,
    columns: ['Rank', 'Country', 'CHIPS score'],
    rows,
    note: `Median ${scoreText(source.median)} · range ${scoreText(source.min)}–${scoreText(source.max)} · scores 0–100.`,
  };
}

function top15Table(rows: Top15RowModel[]): PaneTableModel {
  return {
    caption: 'The top 15 CHIPS scores, highest ranked first.',
    columns: ['Rank', 'Country', 'CHIPS score'],
    rows: rows.map((row) => [formatRank(row.rank), row.label, row.scoreText]),
    note:
      rows.length >= 13
        ? `Places 4–13 span ${rows[3].scoreText} → ${rows[12].scoreText}.`
        : 'Scores 0–100.',
  };
}

/* ---------------------------------------------------------- pane 3 */

/** The framework order, read from chips.json: CONNECT → SUSTAINABILITY. */
const PILLAR_ORDER: string[] = pillars.map((pillar) => pillar.id);

function shortNames(): Map<string, string> {
  // Country short names are method-independent; chips.json is the edition's
  // own name table, so it is the right source here.
  return new Map(
    defaultData.scores.map((row) => [row.iso3, row.shortName || row.country]),
  );
}

/**
 * Pane 3 is a decomposition, so the one number that must not be recomputed is
 * the segment length: each width is `contribution` straight from the exporter,
 * which is pillar score × nominal weight. Only the pixels between two
 * contributions are ours, and those are a plain cumulative sum.
 */
function buildCompositionChart(id: string): CompositionChartModel | null {
  const source = methodBlock(id)?.composition;
  if (!source?.length) return null;

  const rows = [...source].sort((a, b) => a.rank - b.rank).slice(0, 10);
  const names = shortNames();
  const peak = Math.max(...rows.map((row) => row.score));
  const max = Math.max(10, Math.ceil((peak * 100) / 10) * 10);
  const x = scaleLinear().domain([0, max]).range([0, 100]);

  const models = rows.map((row) => {
    let cursor = 0;
    const segments = PILLAR_ORDER.filter((id) =>
      row.pillars.some((pillar) => pillar.id === id),
    ).map((id) => {
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

    // The bar's total is the sum of what it draws; the printed composite is
    // the exporter's 2-dp score. Both are shown, and the check below keeps
    // them from drifting apart.
    const total = segments.reduce((sum, segment) => sum + segment.contribution, 0);
    return {
      iso3: row.iso3,
      label: names.get(row.iso3) ?? row.country,
      rank: row.rank,
      total,
      totalText: formatComposite(row.score),
      segments,
    };
  });

  const weights = rows[0]?.pillars ?? [];
  const legend = PILLAR_ORDER.filter((id) =>
    weights.some((pillar) => pillar.id === id),
  ).map((id) => {
    const weight = weights.find((pillar) => pillar.id === id)?.weight;
    return {
      id,
      label: id,
      weightText: weight === undefined ? '' : formatPercent(weight, 1),
    };
  });

  const ticks = Array.from({ length: max / 10 + 1 }, (_, index) => ({
    pct: x(index * 10),
    label: String(index * 10),
  }));

  const leader = models[0];
  return {
    kind: 'composition',
    rows: models,
    pillarOrder: PILLAR_ORDER,
    legend,
    ticks,
    ariaLabel:
      `Stacked bars for the top ${models.length} CHIPS scores, each split into its five ` +
      `weighted pillar contributions. ${leader.label} leads with ${leader.totalText}, ` +
      `made of ${leader.segments
        .map((segment) => `${segment.id} ${segment.text}`)
        .join(', ')}; the five segments sum to the score.`,
  };
}

function compositionTable(model: CompositionChartModel): PaneTableModel {
  return {
    caption: `The top ${model.rows.length} CHIPS scores, split into their five weighted pillar contributions.`,
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
    note:
      'Contribution is pillar score × nominal weight, on the 0–100 scale. ' +
      'The five contributions sum to the composite before the final 2-dp rounding.',
  };
}

/**
 * Rank ticks that do not collide. Projected backwards so a crowded end keeps
 * the outer rank (71) rather than an inner multiple of ten (70).
 */
function spacedTicks(
  ranks: number[],
  project: (rank: number) => number,
  minGap: number,
): Array<{ rank: number; pos: number }> {
  const unique = [...new Set(ranks)].sort((a, b) => a - b);
  const kept: Array<{ rank: number; pos: number }> = [];
  for (let index = unique.length - 1; index >= 0; index -= 1) {
    const rank = unique[index];
    const pos = project(rank);
    const next = kept[kept.length - 1];
    if (!next || Math.abs(next.pos - pos) >= minGap) kept.push({ rank, pos });
  }
  return kept.reverse();
}

/* ---------------------------------------------------------- pane 4 */

/**
 * All countries' ranks in one pillar, for the method being rendered.
 * `overview.json` carries India's five pillar ranks but not the other 70
 * countries' per-pillar ranks, so the strip reads `chips.json` — which carries
 * one scored table per method. The block and the strip are therefore the same
 * ranking, whichever method is active.
 */
function pillarRanks(id: string, methodId: string): number[] {
  return (scales[methodId] ?? defaultData).scores
    .map((row) => row.pillars[id]?.rank)
    .filter((rank): rank is number => typeof rank === 'number' && Number.isFinite(rank));
}

/** Spread countries that share a rank into lanes so the strip shows density. */
function tieOffsets(ranks: number[], x: (rank: number) => number): VerdictPointModel[] {
  const groups = new Map<number, number[]>();
  for (const rank of ranks) {
    const group = groups.get(rank) ?? [];
    group.push(rank);
    groups.set(rank, group);
  }
  const lanes = new Map<number, number>();
  return ranks.map((rank) => {
    const group = groups.get(rank) ?? [];
    const index = lanes.get(rank) ?? 0;
    lanes.set(rank, index + 1);
    const offset = group.length === 1 ? 0 : (index - (group.length - 1) / 2) * 5.5;
    return { rank, xPct: x(rank), dy: Math.max(-8, Math.min(8, offset)) };
  });
}

function verdictSource(methodId: string): {
  pillars: Array<{ id: string; score: number; rank: number; of: number }>;
  best: { id: string; rank: number };
  worst: { id: string; rank: number };
  of: number;
  overallRank: number;
} | null {
  const block = methodBlock(methodId);
  if (block?.india) {
    const india = block.india;
    const of = india.pillars[0]?.of ?? overview?.meta?.countries ?? defaultData.scores.length;
    return {
      pillars: india.pillars.map((pillar) => ({
        id: pillar.id,
        score: pillar.score,
        rank: pillar.rank ?? 0,
        of: pillar.of ?? of,
      })),
      best: india.best ?? { id: india.pillars[0]?.id ?? '', rank: 0 },
      worst:
        india.worst ?? {
          id: india.pillars[india.pillars.length - 1]?.id ?? '',
          rank: 0,
        },
      of,
      overallRank: india.rank,
    };
  }

  const row = (scales[methodId] ?? defaultData).scores.find((item) => item.iso3 === 'IND');
  if (!row) return null;
  const ranked = PILLAR_ORDER.map((id) => ({
    id,
    score: row.pillars[id]?.score ?? 0,
    rank: row.pillars[id]?.rank ?? 0,
    of: pillarRanks(id, methodId).length,
  }));
  const sorted = [...ranked].sort((a, b) => a.rank - b.rank);
  return {
    pillars: ranked,
    best: { id: sorted[0].id, rank: sorted[0].rank },
    worst: { id: sorted[sorted.length - 1].id, rank: sorted[sorted.length - 1].rank },
    of: ranked[0]?.of ?? defaultData.scores.length,
    overallRank: row.rank,
  };
}

function buildIndiaChart(methodId: string): IndiaChartModel | null {
  const source = verdictSource(methodId);
  if (!source?.pillars.length) return null;

  const total = source.of;
  // Inset the range so a marker at rank 1 or rank N is not clipped.
  const x = scaleLinear().domain([1, total]).range([3, 97]);
  const rowHeight = 52;

  const rows = PILLAR_ORDER.filter((id) =>
    source.pillars.some((pillar) => pillar.id === id),
  ).map((id) => {
    const pillar = source.pillars.find((item) => item.id === id);
    const ranks = pillarRanks(id, methodId);
    const sorted = [...ranks].sort((a, b) => a - b);
    const median =
      sorted.length === 0
        ? 0
        : sorted.length % 2 === 0
          ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
          : sorted[Math.floor(sorted.length / 2)];
    return {
      id,
      scoreText: formatComposite(pillar?.score ?? 0),
      rank: pillar?.rank ?? 0,
      of: pillar?.of ?? total,
      points: tieOffsets(ranks, x),
      indiaXPct: x(pillar?.rank ?? 1),
      best: sorted[0] ?? 0,
      median,
      worst: sorted[sorted.length - 1] ?? 0,
    };
  });

  const best = rows.find((row) => row.id === source.best.id) ?? rows[0];
  const worst = rows.find((row) => row.id === source.worst.id) ?? rows[rows.length - 1];

  const ticks = spacedTicks(
    [1, ...Array.from({ length: Math.floor(total / 10) }, (_, i) => (i + 1) * 10), total],
    x,
    4,
  ).map((tick) => ({ pct: tick.pos, label: String(tick.rank) }));

  return {
    kind: 'india',
    rows,
    ticks,
    rowHeight,
    height: rows.length * rowHeight + 34,
    best: { id: best.id, rank: best.rank },
    worst: { id: worst.id, rank: worst.rank },
    of: total,
    ariaLabel:
      `Dot plot of India's rank in each of the five pillars against all ${total} countries' ` +
      `ranks in that pillar. India is ${ordinal(best.rank)} in ${best.id} and ` +
      `${ordinal(worst.rank)} in ${worst.id}. Each dot is one country's rank within the pillar; ` +
      '1 is best.',
  };
}

function indiaTable(model: IndiaChartModel, overallRank: number, methodId: string): PaneTableModel {
  const names = shortNames();
  const leaders = new Map<string, string>();
  for (const row of model.rows) {
    const leader = (scales[methodId] ?? defaultData).scores
      .filter((item) => item.pillars[row.id]?.rank === 1)
      .map((item) => names.get(item.iso3) ?? item.country)
      .sort((a, b) => a.localeCompare(b));
    leaders.set(row.id, leader[0] ?? '—');
  }
  return {
    caption: `India's rank in each pillar, within all ${model.of} countries.`,
    columns: ['Pillar', "India's rank", 'Of', "India's score", 'Pillar leader', 'Median rank'],
    numericColumns: [1, 2, 3, 5],
    rows: model.rows.map((row) => [
      row.id,
      formatRank(row.rank),
      formatRank(row.of),
      row.scoreText,
      leaders.get(row.id) ?? '—',
      row.median % 1 === 0 ? String(row.median) : row.median.toFixed(1),
    ]),
    note:
      `Ranks are within each pillar, from 1 to ${model.of}. A pillar rank is not the ` +
      `overall rank: India is ${formatRank(overallRank)} overall.`,
  };
}

/* ---------------------------------------------------------- pane 5 */

interface MovementSource {
  years: number[];
  countries: Array<{
    iso3: string;
    country: string;
    ranks: Record<string, number | null>;
    scores: Record<string, number | null>;
  }>;
  total: number;
}

type SeriesPayload = {
  series: Array<{
    iso3: string;
    year: number;
    rank: number | null;
    overall?: number;
  }>;
};

function seriesFor(methodId: string): SeriesPayload | null {
  const series = rawSeries as unknown as {
    methods: Record<string, SeriesPayload>;
  };
  return series.methods[methodId] ?? series.methods[methodComparison.baselineId] ?? null;
}

/** Scores keyed by ISO-3 and year, from the comparison series. */
function seriesScores(methodId: string): Map<string, Record<string, number>> {
  const scores = new Map<string, Record<string, number>>();
  for (const row of seriesFor(methodId)?.series ?? []) {
    if (typeof row.overall !== 'number' || !Number.isFinite(row.overall)) continue;
    const entry = scores.get(row.iso3) ?? {};
    entry[String(row.year)] = row.overall;
    scores.set(row.iso3, entry);
  }
  return scores;
}

/** Ranks keyed by ISO-3 and year, from the comparison series. */
function seriesRanks(methodId: string): Map<string, Record<string, number | null>> {
  const ranks = new Map<string, Record<string, number | null>>();
  for (const row of seriesFor(methodId)?.series ?? []) {
    const entry = ranks.get(row.iso3) ?? {};
    entry[String(row.year)] = typeof row.rank === 'number' ? row.rank : null;
    ranks.set(row.iso3, entry);
  }
  return ranks;
}

/**
 * `movement` is inside each method's block: no year, no country count and no
 * number of editions is written here, so a 2027 payout extends the chart
 * without a code change — and each method carries its own scores.
 */
function movementSource(methodId: string): MovementSource {
  const total = overview?.meta?.countries ?? defaultData.scores.length;
  const block = methodBlock(methodId);
  if (block?.movement?.countries?.length && block.movement.years?.length) {
    const fallbackScores = seriesScores(methodId);
    return {
      years: block.movement.years.map(Number).sort((a, b) => a - b),
      countries: block.movement.countries.map((country) => ({
        ...country,
        scores: country.scores ?? fallbackScores.get(country.iso3) ?? {},
      })),
      total,
    };
  }

  // Fallback: the comparison series already in src/data, so the pane still
  // knows its years and panel shape when overview.json is absent.
  const years = [...((rawSeries as unknown as { meta: { years: number[] } }).meta.years)].sort(
    (a, b) => a - b,
  );
  const names = new Map(defaultData.scores.map((row) => [row.iso3, row.country]));
  const scores = seriesScores(methodId);
  const ranks = seriesRanks(methodId);
  const byCountry = new Map<string, Record<string, number | null>>();
  for (const row of seriesFor(methodId)?.series ?? []) {
    const entry = byCountry.get(row.iso3) ?? {};
    entry[String(row.year)] = row.rank;
    byCountry.set(row.iso3, entry);
  }
  const countries = [...byCountry.entries()]
    .filter(([, entry]) => years.filter((year) => entry[String(year)] != null).length >= 2)
    .map(([iso3, entry]) => ({
      iso3,
      country: names.get(iso3) ?? iso3,
      ranks: entry,
      scores: scores.get(iso3) ?? ({} as Record<string, number | null>),
    }));
  return { years, countries, total };
}

/** Median of a numeric list; 0 for an empty list. */
function medianValue(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
}

/** Signed change in points, one decimal, with a true minus sign. */
function pointsText(delta: number | null): string {
  if (delta === null) return '—';
  const points = Math.round(delta * 1000) / 10;
  if (points === 0) return '0.0';
  return points > 0 ? `+${points.toFixed(1)}` : `−${Math.abs(points).toFixed(1)}`;
}

function signedPlaces(delta: number | null): string {
  if (delta === null) return '—';
  if (delta === 0) return '0';
  return delta > 0 ? `+${delta}` : `−${Math.abs(delta)}`;
}

/**
 * Pane 5: one dumbbell per country, both ends on a fixed 0–100 score axis.
 * Rows are ordered by the last edition's score, so the eye reads the field
 * rather than a rank churn. The rank comparison is still available — in the
 * table, where a rank can be printed without being encoded.
 */
function buildMovementChart(source: MovementSource): MovementChartModel {
  const { years } = source;
  const names = shortNames();
  // Inset the range so a marker at 0 or 100 is never clipped by the row.
  const x = scaleLinear().domain([0, 100]).range([1.5, 98.5]);

  const rows: MovementRowModel[] = source.countries.map((country) => {
    const scores = country.scores ?? {};
    const points: MovementPointModel[] = years.flatMap((year) => {
      const value = scores[String(year)];
      if (typeof value !== 'number' || !Number.isFinite(value)) return [];
      return [{ year, score: value, xPct: x(value * 100) }];
    });

    const byYear = new Map(points.map((point) => [point.year, point]));
    const segments = movementRuns(years, scores).flatMap((run) => {
      const from = byYear.get(run.fromYear);
      const to = byYear.get(run.toYear);
      return from && to ? [{ from, to }] : [];
    });

    const first = points[0];
    const last = points[points.length - 1];
    const deltaPoints =
      first && last && points.length >= 2 ? last.score - first.score : null;
    const ranks = country.ranks ?? {};
    const firstRank = years
      .map((year) => ranks[String(year)])
      .find((value) => typeof value === 'number');
    const lastRank = [...years]
      .reverse()
      .map((year) => ranks[String(year)])
      .find((value) => typeof value === 'number');

    return {
      iso3: country.iso3,
      label: names.get(country.iso3) ?? country.country,
      highlighted: false,
      points,
      segments,
      deltaPoints,
      deltaText: pointsText(deltaPoints),
      lastScoreText: last ? scoreText(last.score) : '—',
      rankChange:
        typeof firstRank === 'number' && typeof lastRank === 'number'
          ? lastRank - firstRank
          : null,
      ranks,
    };
  });

  // Five largest absolute score changes; ties broken by name so the choice is
  // stable between builds. This is the pane's own highlight rule — not rank.
  const movers = rows
    .filter((row): row is MovementRowModel & { deltaPoints: number } =>
      row.deltaPoints !== null,
    )
    .sort(
      (a, b) =>
        Math.abs(b.deltaPoints) - Math.abs(a.deltaPoints) ||
        a.label.localeCompare(b.label),
    )
    .slice(0, Math.min(5, rows.length));
  const highlighted = new Set(movers.map((row) => row.iso3));

  const ordered = rows
    .map((row) => ({ ...row, highlighted: highlighted.has(row.iso3) }))
    .sort((a, b) => {
      const lastA = a.points[a.points.length - 1]?.score ?? Number.NEGATIVE_INFINITY;
      const lastB = b.points[b.points.length - 1]?.score ?? Number.NEGATIVE_INFINITY;
      return lastB - lastA || a.label.localeCompare(b.label);
    });

  const count = ordered.length;
  const biggest = movers[0];
  const biggestText = biggest
    ? `${biggest.label} changes by ${biggest.deltaText} points`
    : 'the largest score changes are highlighted';

  const caveat = `${count} of ${source.total} countries, scored in ${
    years.length === 2 ? 'both editions' : `all ${years.length} editions`
  }`;

  return {
    kind: 'movement',
    years,
    rows: ordered,
    // A fixed 0–100 axis keeps a one-point move one point wide.
    ticks: [0, 20, 40, 60, 80, 100].map((value) => ({
      pct: x(value),
      label: String(value),
    })),
    count,
    total: source.total,
    caveat,
    height: ordered.length * 26 + 34,
    ariaLabel:
      `Dumbbell chart of CHIPS scores in ${years.join(' and ')} for ${count} countries, ` +
      `on a fixed 0–100 axis, sorted by the ${years[years.length - 1]} score. ` +
      `${biggestText}; the five largest changes are marked. Rank changes are in the table.`,
  };
}

function movementTable(model: MovementChartModel): PaneTableModel {
  const scoreFor = (row: MovementRowModel, year: number): string => {
    const point = row.points.find((item) => item.year === year);
    return point ? scoreText(point.score) : '—';
  };
  const rankFor = (row: MovementRowModel, year: number): string => {
    const value = row.ranks[String(year)];
    return typeof value === 'number' ? formatRank(value) : '—';
  };

  return {
    caption: `Score and rank in each edition for the ${model.count} countries scored at least twice.`,
    columns: [
      'Country',
      ...model.years.map((year) => `${year} score`),
      'Δ points',
      ...model.years.map((year) => `${year} rank`),
      'Δ rank',
    ],
    numericColumns: [
      ...model.years.map((_, index) => index + 1),
      model.years.length + 1,
      ...model.years.map((_, index) => model.years.length + 2 + index),
      model.years.length * 2 + 2,
    ],
    rows: model.rows.map((row) => [
      row.label,
      ...model.years.map((year) => scoreFor(row, year)),
      row.deltaText,
      ...model.years.map((year) => rankFor(row, year)),
      signedPlaces(row.rankChange),
    ]),
    note:
      `Scores are the edition's own composite (2 dp on 0–100); ranks run 1–${model.total}. ` +
      'A positive Δ rank means a lower position in the last edition. Scores are recomputed ' +
      'within each edition, so a Δ points is not a like-for-like performance change.',
  };
}

/* ---------------------------------------------------------- pane 6 */

interface ScaleMovementSourceRow {
  iso3: string;
  country: string;
  rankFull: number;
  rankZ: number;
  delta: number;
}

function scaleMovementSource(): ScaleMovementSourceRow[] {
  const movers = overview?.scaleMovement?.movers;
  if (movers?.length) {
    return movers.map((row) => ({
      iso3: row.iso3,
      country: row.country,
      rankFull: row.rankFull,
      rankZ: row.rankZ,
      delta: row.delta,
    }));
  }
  // Fallback: derive the same comparison from the two chips.json payloads.
  const full = new Map(defaultData.scores.map((row) => [row.iso3, row.rank]));
  const other = methodComparison.otherId ? scalesForMethod(methodComparison.otherId) : null;
  if (!other) return [];
  return other
    .map((row) => {
      const rankFull = full.get(row.iso3);
      if (typeof rankFull !== 'number') return null;
      return {
        iso3: row.iso3,
        country: row.country,
        rankFull,
        rankZ: row.rank,
        delta: row.rank - rankFull,
      };
    })
    .filter((row): row is ScaleMovementSourceRow => row !== null)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.country.localeCompare(b.country));
}

function scalesForMethod(id: string): Array<{ iso3: string; country: string; rank: number }> {
  return (scales[id]?.scores ?? defaultData.scores).map((row) => ({
    iso3: row.iso3,
    country: row.country,
    rank: row.rank,
  }));
}

/**
 * Pane 6: the 10 largest rank differences between min–max and z-score,
 * diverging from a zero line. `delta = rankZ − rankFull`, so a bar to the left
 * means the z-score puts the country higher. Direction is carried by the side
 * of the zero line and the printed ranks, not by colour.
 */
function buildScaleMovementChart(source: ScaleMovementSourceRow[]): ScaleMovementChartModel {
  const total = source.length;
  const changed = source.filter((row) => row.delta !== 0).length;
  const maxDelta = Math.max(1, ...source.map((row) => Math.abs(row.delta)));

  const rows = [...source]
    .sort(
      (a, b) =>
        Math.abs(b.delta) - Math.abs(a.delta) || a.country.localeCompare(b.country),
    )
    .slice(0, 10)
    .map((row) => {
      const widthPct = (Math.abs(row.delta) / maxDelta) * 48;
      const negative = row.delta < 0;
      return {
        iso3: row.iso3,
        label: row.country,
        rankFull: row.rankFull,
        rankZ: row.rankZ,
        delta: row.delta,
        deltaText: signedPlaces(row.delta),
        rankText: `${row.rankFull} → ${row.rankZ}`,
        startPct: negative ? 50 - widthPct : 50,
        widthPct,
        side: negative ? ('better' as const) : ('worse' as const),
      };
    });

  const top = [...source].sort(
    (a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.country.localeCompare(b.country),
  )[0];

  const headline = top
    ? `${changed} of ${total} countries change rank between the two methods; ` +
      `${top.country} moves ${Math.abs(top.delta)} place${Math.abs(top.delta) === 1 ? '' : 's'}.`
    : 'No country changes rank between the two methods.';

  const ticks = [0, 25, 50, 75, 100].map((value) => {
    if (value === 50) return { pct: value, label: '0' };
    const places = Math.round((Math.abs(value - 50) / 48) * maxDelta);
    return { pct: value, label: value < 50 ? `−${places}` : `+${places}` };
  });

  return {
    kind: 'scaleMovement',
    rows,
    ticks,
    total,
    changed,
    headline,
    gainLabel: 'higher under z',
    lossLabel: 'lower under z',
    ariaLabel:
      `Diverging bars of rank change between min–max and z-score scaling for the ` +
      `${rows.length} largest movers. ${rows
        .slice(0, 3)
        .map((row) => `${row.label} ${row.rankText}, ${row.deltaText}`)
        .join('; ')}. ` +
      `Negative means the z-score ranks the country higher. ${headline}`,
  };
}

function scaleMovementTable(model: ScaleMovementChartModel): PaneTableModel {
  const rows = [...model.rows].sort(
    (a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.label.localeCompare(b.label),
  );
  const all = (overview?.scaleMovement?.movers ?? [])
    .map((row) => ({ ...row }))
    .sort(
      (a, b) =>
        Math.abs(b.delta) - Math.abs(a.delta) || a.country.localeCompare(b.country),
    );
  const source = all.length
    ? all.map((row) => ({
        label: row.country,
        rankFull: row.rankFull,
        rankZ: row.rankZ,
        delta: row.delta,
      }))
    : rows.map((row) => ({
        label: row.label,
        rankFull: row.rankFull,
        rankZ: row.rankZ,
        delta: row.delta,
      }));

  return {
    caption: `Rank under min–max and under z-score for all ${source.length} countries.`,
    columns: ['Country', 'Min–max rank', 'Z-score rank', 'Δ rank'],
    numericColumns: [1, 2, 3],
    rows: source.map((row) => [
      row.label,
      formatRank(row.rankFull),
      formatRank(row.rankZ),
      signedPlaces(row.delta),
    ]),
    note:
      `Δ rank = z-score rank − min–max rank, so a negative number means the z-score ` +
      `ranks the country higher. ${model.changed} of ${model.total} countries change rank.`,
  };
}

/* ---------------------------------------------------------- panes 7–8 */

/** Compact US dollars: $16.4bn, $604bn, $3.96tn, $30.8tn. */
function formatUsd(value: number): string {
  const scale = value >= 1e12 ? { divisor: 1e12, suffix: 'tn' } : { divisor: 1e9, suffix: 'bn' };
  const scaled = value / scale.divisor;
  const digits = scaled >= 100 ? 0 : scaled >= 10 ? 1 : 2;
  return `$${Number(scaled.toFixed(digits))}${scale.suffix}`;
}

const SCATTER_HEIGHT = 360;
const SCATTER_TOP = 18;
const SCATTER_BOTTOM = 306;
const SCATTER_LEFT_PCT = 10;
const SCATTER_RIGHT_PCT = 96;

function scoreAxisMax(scores: number[]): number {
  const peak = scores.length ? Math.max(...scores) * 100 : 0;
  return Math.max(50, Math.ceil(peak / 10) * 10);
}

function sizeVsScoreSource(methodId: string) {
  return methodBlock(methodId)?.sizeVsScore ?? [];
}

/**
 * Pane 7: GDP on a log x-axis (three orders of magnitude) against the CHIPS
 * score. Only four countries are named — the two largest scores, the largest
 * economy and one high-scoring smaller economy — so the scatter reads as a
 * field rather than a label cloud.
 */
function buildSizeVsScoreChart(methodId: string): ScatterChartModel | null {
  const source = sizeVsScoreSource(methodId).filter(
    (row) => Number.isFinite(row.gdp) && row.gdp > 0,
  );
  if (!source.length) return null;

  const gdp = source.map((row) => row.gdp);
  const min = Math.min(...gdp);
  const max = Math.max(...gdp);
  const x = scaleLog()
    .domain([min / 1.2, max * 1.6])
    .range([SCATTER_LEFT_PCT, SCATTER_RIGHT_PCT]);
  const yMax = scoreAxisMax(source.map((row) => row.score));
  const y = scaleLinear()
    .domain([0, yMax])
    .range([SCATTER_BOTTOM, SCATTER_TOP]);

  const labelled = new Set(['USA', 'CHN', 'IND']);
  // One high-scoring smaller economy: the best score among countries below
  // $1tn, chosen from the data rather than fixed by name.
  const smaller = [...source]
    .filter((row) => row.gdp < 1e12 && !labelled.has(row.iso3))
    .sort((a, b) => b.score - a.score || a.country.localeCompare(b.country))[0];
  if (smaller) labelled.add(smaller.iso3);

  const points: ScatterPointModel[] = source.map((row) => {
    const isLabelled = labelled.has(row.iso3);
    const xPct = x(row.gdp);
    return {
      iso3: row.iso3,
      label: SHORT_CHART_NAMES[row.iso3] ?? row.country,
      score: row.score,
      gdp: row.gdp,
      xPct,
      y: y(row.score * 100),
      labelXPct: isLabelled ? xPct : undefined,
      labelY: isLabelled ? y(row.score * 100) - 11 : undefined,
      labelAnchor: xPct > 88 ? 'end' : xPct < 14 ? 'start' : 'middle',
    };
  });

  // Four ticks across the full range, spaced by decades so the log axis is
  // read as magnitudes rather than raw dollar counts.
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
      `Scatter of GDP 2025 in current US dollars on a logarithmic axis against the ` +
      `CHIPS score, ${points.length} countries. ` +
      `${points
        .filter((point) => point.labelY !== undefined)
        .map((point) => `${point.label} ${formatUsd(point.gdp as number)}, ${scoreText(point.score)}`)
        .join('; ')}. The Absolute edition scores absolute volumes, so size and score are ` +
      'related partly by construction.',
  };
}

function sizeVsScoreTable(methodId: string): PaneTableModel {
  const source = [...sizeVsScoreSource(methodId)].sort((a, b) => a.rank - b.rank);
  return {
    caption: `CHIPS score and 2025 GDP for all ${source.length} countries, highest ranked first.`,
    columns: ['Rank', 'Country', 'CHIPS score', `GDP ${overview?.meta?.gdpYear ?? 2025}`],
    numericColumns: [0, 2, 3],
    rows: source.map((row) => [
      formatRank(row.rank),
      row.country,
      scoreText(row.score),
      formatUsd(row.gdp),
    ]),
    note:
      'GDP is current US dollars, joined by ISO-3 code. The repo publishes no population ' +
      'series, so no per-capita figure is shown. A larger economy is not automatically a ' +
      'higher score: the relationship is partly definitional in the Absolute edition.',
  };
}

/** Coverage below this line is flagged in pane 8. */
const COVERAGE_THRESHOLD = 0.8;

function coverageSource(methodId: string) {
  return methodBlock(methodId)?.coverage ?? [];
}

/**
 * Pane 8: coverage against score. The nine countries below 80% coverage are
 * marked, not hidden; the note about unscored cells is computed from the
 * engine's sub-pillar statuses rather than quoted.
 */
function buildCoverageChart(methodId: string): ScatterChartModel | null {
  const source = coverageSource(methodId);
  if (!source.length) return null;

  const x = scaleLinear()
    .domain([0.65, 1])
    .range([SCATTER_LEFT_PCT, SCATTER_RIGHT_PCT]);
  const yMax = scoreAxisMax(source.map((row) => row.score));
  const y = scaleLinear()
    .domain([0, yMax])
    .range([SCATTER_BOTTOM, SCATTER_TOP]);

  const below = source.filter((row) => row.coverage < COVERAGE_THRESHOLD);
  const points: ScatterPointModel[] = source.map((row) => ({
    iso3: row.iso3,
    label: row.country,
    score: row.score,
    coverage: row.coverage,
    xPct: x(row.coverage),
    y: y(row.score * 100),
    belowThreshold: row.coverage < COVERAGE_THRESHOLD,
  }));

  const unscoredCells = (scales[methodId] ?? defaultData).scores.reduce(
    (total, row) => total + notScoredSubPillars(row),
    0,
  );

  return {
    kind: 'coverage',
    points,
    xTicks: [0.7, 0.8, 0.9, 1].map((value) => ({
      pct: x(value),
      label: formatPercent(value, 0),
    })),
    yTicks: Array.from({ length: yMax / 10 + 1 }, (_, index) => ({
      y: y(index * 10),
      label: String(index * 10),
    })),
    height: SCATTER_HEIGHT,
    plotLeftPct: SCATTER_LEFT_PCT,
    plotRightPct: SCATTER_RIGHT_PCT,
    thresholdPct: x(COVERAGE_THRESHOLD),
    belowThreshold: below.length,
    unscoredCells,
    ariaLabel:
      `Scatter of data coverage against CHIPS score for ${points.length} countries. ` +
      `${below.length} countries sit below 80% coverage and are marked. ` +
      `${unscoredCells} country-by-sub-pillar cells are unscored across the edition.`,
  };
}

function coverageTable(methodId: string, model: ScatterChartModel): PaneTableModel {
  const source = [...coverageSource(methodId)].sort((a, b) => a.rank - b.rank);
  return {
    caption: `CHIPS score and data coverage for all ${source.length} countries, highest ranked first.`,
    columns: ['Rank', 'Country', 'CHIPS score', 'Coverage', 'Indicators'],
    numericColumns: [0, 2, 3, 4],
    rows: source.map((row) => [
      formatRank(row.rank),
      row.country,
      scoreText(row.score),
      formatPercent(row.coverage, 1),
      `${row.indicatorsPresent} / ${row.indicatorsTotal}`,
    ]),
    note:
      `${model.unscoredCells ?? 0} country × sub-pillar cells are unscored in this edition; ` +
      'the weight of a missing indicator is redistributed across the ones that remain. ' +
      'Coverage is the weighted share of the indicator set a country has data for.',
  };
}

/**
 * The stacked bars are read straight from `contribution`, which the exporter
 * computes as score × nominal weight. Check the arithmetic once per method at
 * build time: a silent drift there would make pane 3 an illustration, not a
 * decomposition.
 *
 * `composition[].score` is the exporter's composite rounded to 4 decimals,
 * while the contributions carry full precision, so the tolerance is half of
 * that last digit rather than 1e-9. The sum matches the unrounded composite
 * exactly; this guard catches a genuine mismatch, not the rounding step.
 */
function checkComposition(methodId: string): void {
  for (const country of methodBlock(methodId)?.composition ?? []) {
    const sum = country.pillars.reduce(
      (total, pillar) => total + (pillar.contribution ?? 0),
      0,
    );
    if (Math.abs(sum - country.score) > 5e-5) {
      console.warn(
        `[overview] ${methodId} ${country.iso3}: pillar contributions sum to ${sum}, score is ${country.score}`,
      );
    }
  }
}

/**
 * The dumbbells carry their own per-edition scores in the method block; the
 * comparison series is the second witness for the same numbers. If the two
 * exports ever disagree on a rank, the chart and the table would tell
 * different stories — so compare them at build time instead of trusting it.
 */
function checkMovementRanks(methodId: string): void {
  const series = seriesRanks(methodId);
  for (const country of movementSource(methodId).countries) {
    for (const [year, rank] of Object.entries(country.ranks)) {
      const other = (series.get(country.iso3) ?? {})[year];
      if (rank !== null && other != null && rank !== other) {
        console.warn(
          `[overview] ${methodId} ${country.iso3} ${year}: movement rank ${rank}, series rank ${other}`,
        );
      }
    }
  }
}

function methodNote(method: string): string {
  return (
    `Edition ${meta.edition} · ${methodShortLabel(method)} scaling · ` +
    `${meta.countries} countries · ${meta.leaves} indicators · ` +
    'CHIPS composite to 2 decimals; pillar and indicator scores to 1.'
  );
}

/** Correlation printed in pane 7's caption, from the active method's block. */
function correlationText(correlation: OverviewCorrelationJson | undefined): string {
  if (!correlation) return '';
  const parts = [
    `ρ Spearman ${correlation.spearman.toFixed(4)} and Pearson ${correlation.pearson.toFixed(4)}`,
  ];
  if (
    typeof correlation.spearmanExTop2 === 'number' &&
    typeof correlation.pearsonExTop2 === 'number'
  ) {
    parts.push(
      `excluding the USA and China, ${correlation.spearmanExTop2.toFixed(4)} and ` +
        `${correlation.pearsonExTop2.toFixed(4)}`,
    );
  }
  return parts.join('; ');
}

/**
 * Build one method's eight panes. Every number in the block comes from that
 * method's slice of the payload; pane 6 is the one exception and is built once
 * outside this function, because it compares the methods rather than following
 * the toggle.
 */
function buildMethodPanes(
  methodId: string,
  scaleChart: ScaleMovementChartModel | null,
): { panes: PaneModel[]; field: FieldSource } {
  const note = methodNote(methodId);
  const field = fieldSource(methodId);
  const top15 = top15Source(methodId);
  const max = axisMax(field.values.map((row) => row.score));
  const fieldChart = buildFieldChart(field);
  const topChart = buildTop15Chart(top15, max);
  const movement = movementSource(methodId);
  const movementChart = buildMovementChart(movement);
  const verdict = verdictSource(methodId);
  const india = {
    best: verdict?.best ?? { id: '—', rank: 0 },
    worst: verdict?.worst ?? { id: '—', rank: 0 },
    of: verdict?.of ?? defaultData.scores.length,
  };
  const composition = buildCompositionChart(methodId);
  const indiaChart = buildIndiaChart(methodId);
  const sizeChart = buildSizeVsScoreChart(methodId);
  const coverageChart = buildCoverageChart(methodId);
  const overallRank = verdict?.overallRank ?? 0;
  const correlation = methodBlock(methodId)?.correlation;
  const yearsText = movement.years.join(' → ');
  const scoreChanges = movementChart.rows
    .map((row) => row.deltaPoints)
    .filter((value): value is number => value !== null)
    .map((value) => Math.abs(value * 100));
  const medianScoreMove = medianValue(scoreChanges);
  const biggestMove = movementChart.rows
    .filter(
      (row): row is MovementRowModel & { deltaPoints: number } =>
        row.deltaPoints !== null,
    )
    .sort(
      (a, b) =>
        Math.abs(b.deltaPoints) - Math.abs(a.deltaPoints) ||
        a.label.localeCompare(b.label),
    )[0];
  const firstYear = movement.years[0];
  const lastYear = movement.years[movement.years.length - 1];
  const poolText =
    firstYear === 2025 && lastYear === 2026
      ? // The 2025 Absolute edition carries 59 countries; that count predates
        // `meta.countries` and is documented in docs/ai-index-ia.md. Any other
        // window falls back to the payload's own total.
        `the pool grew from 59 to ${movement.total} countries`
      : `the pool is ${movement.total} countries in ${lastYear}`;

  checkComposition(methodId);
  checkMovementRanks(methodId);

  const panes: PaneModel[] = [
    {
      number: 1,
      title: 'The field',
      what: `All ${field.values.length} scores, one dot per country, with the edition median marked.`,
      caption:
        'Every country the index scores, at once — no cut-off and no grouping. ' +
        'The median is where the middle of the field sits, not a target. ' +
        'India is marked because the next panes keep returning to it.',
      chart: fieldChart,
      table: fieldTable(field),
      tableFallback: null,
      methodNote: note,
    },
    {
      number: 2,
      title: 'The podium and the pack',
      what: 'The top 15 on the same scale, with the first three separated from the rest.',
      caption:
        `Places 4–13 span ${topChart.spanFrom} → ${topChart.spanTo}: ten countries ` +
        'inside a handful of points, while the top three sit well above them. ' +
        'A rank is a position in that line, not a grade.',
      chart: topChart,
      table: top15Table(topChart.rows),
      tableFallback: null,
      methodNote: note,
    },
    {
      number: 3,
      title: 'Anatomy of a score',
      what: 'Each top-10 score split into its five weighted pillar contributions.',
      caption:
        'This is a decomposition, not an illustration: at the published pillar weights, ' +
        'a country’s five contributions reconstruct its CHIPS score. The bar is the score. ' +
        'Two countries can sit on the same score and be made of different things.',
      chart:
        composition ??
        ({
          kind: 'placeholder',
          note: 'The weighted composition is not in this build.',
        } as const),
      table: composition ? compositionTable(composition) : null,
      tableFallback: composition
        ? null
        : 'No table is shown: without the exporter’s pillar contributions a table here would have to invent them.',
      methodNote: note,
    },
    {
      number: 4,
      title: 'India’s five verdicts',
      what: `India’s rank in each pillar, against all ${india.of} countries.`,
      caption:
        'Each dot is one country’s rank within that pillar; 1 is best. The headline number ' +
        'hides the story: on this scale India ranks ' +
        `${ordinal(india.best.rank)} in ${india.best.id} and ${ordinal(india.worst.rank)} in ` +
        `${india.worst.id}. These are ranks within a pillar, not the overall rank — India is ` +
        `${ordinal(overallRank)} overall.`,
      chart:
        indiaChart ??
        ({
          kind: 'placeholder',
          note: 'The pillar distribution is not in this build.',
        } as const),
      table: indiaChart ? indiaTable(indiaChart, overallRank, methodId) : null,
      tableFallback: indiaChart
        ? null
        : 'No table is shown: the pillar ranks behind this chart are not in this build.',
      methodNote: note,
    },
    {
      number: 5,
      title: 'Movement',
      what:
        `Each country’s CHIPS score in ${yearsText}, one dumbbell per country; ` +
        'rank change is in the table.',
      caption:
        `Rank churn is mostly composition: ${poolText} and the 2025 edition used a smaller ` +
        'indicator set. ' +
        (biggestMove
          ? `On this scale the largest score change is ${biggestMove.label} at ` +
            `${biggestMove.deltaText} points. `
          : '') +
        `The median score move is ${medianScoreMove.toFixed(1)} points. Scores are not strictly ` +
        `like-for-like either — ${methodShortLabel(methodId)} is recomputed within each edition — ` +
        'so the median is the safer reading than the largest change.',
      chart: movementChart,
      table: movementTable(movementChart),
      tableFallback: null,
      methodNote: note,
    },
    {
      number: 6,
      title: 'The same index, two scales',
      what: 'How far each country moves when the same indicators are put on two scales.',
      caption:
        'Min–max and z-score put the same indicators on a 0–100 scale in different ways. ' +
        'No single indicator reorders countries: both are monotone transforms of one column. ' +
        'The composite sums many differently shaped transforms, and a sum does not commute ' +
        'with them, so the league table reorders. This compares two methods on one edition’s ' +
        'data — it is not a time series. This pane always shows both methods, whichever ' +
        'scale the toggle selects.',
      chart:
        scaleChart ??
        ({
          kind: 'placeholder',
          note: 'The two-method comparison is not in this build.',
        } as const),
      table: scaleChart ? scaleMovementTable(scaleChart) : null,
      tableFallback: scaleChart
        ? null
        : 'No table is shown: the two methods’ ranks are not in this build.',
      methodNote: note,
    },
    {
      number: 7,
      title: 'Scale and score',
      what: 'GDP 2025 on a log scale against the CHIPS score, one dot per country.',
      caption:
        `GDP in current US dollars against the CHIPS score, from the Absolute edition` +
        `${overview?.meta?.gdpYear ? ` (GDP ${overview.meta.gdpYear})` : ''}. ` +
        (correlation
          ? `Across the ${correlation.n ?? field.values.length} countries the rank correlation ` +
            `is ${correlationText(correlation)}. `
          : '') +
        'The Absolute edition scores absolute volumes — users, subscribers, connections — so ' +
        'size and score are related partly by construction. That is a property of the edition, ' +
        'not a discovery that richer countries perform better. The repo has no population ' +
        'series, so no per-capita view is shown.',
      chart:
        sizeChart ??
        ({
          kind: 'placeholder',
          note: 'The GDP join is not in this build.',
        } as const),
      table: sizeChart ? sizeVsScoreTable(methodId) : null,
      tableFallback: sizeChart
        ? null
        : 'No table is shown: the GDP join behind this chart is not in this build.',
      methodNote: note,
    },
    {
      number: 8,
      title: 'How much stands behind a score',
      what: 'Data coverage against the composite score, one dot per country.',
      caption:
        'A country with missing data is not automatically penalised: unscored cells are ' +
        'dropped and their weight is redistributed across the indicators that remain. But its ' +
        'score — and so its rank — rests on less than a score built on all ' +
        `${meta.leaves} indicators. ` +
        'Low coverage is a caveat on the rank, not a correction to it.',
      chart:
        coverageChart ??
        ({
          kind: 'placeholder',
          note: 'The coverage payload is not in this build.',
        } as const),
      table: coverageChart ? coverageTable(methodId, coverageChart) : null,
      tableFallback: coverageChart
        ? null
        : 'No table is shown: the coverage figures behind this chart are not in this build.',
      methodNote: note,
    },
  ];

  return { panes, field };
}

/** The scale the site opens on, read from the overview payload's meta. */
export function overviewDefaultScale(): string {
  const metaJson = overview?.meta;
  const ids = metaJson?.methods ?? [];
  return metaJson?.defaultMethod && ids.includes(metaJson.defaultMethod)
    ? metaJson.defaultMethod
    : defaultScale;
}

export function buildOverviewView(): OverviewView {
  const source: 'overview.json' | 'chips.json' = overview ? 'overview.json' : 'chips.json';
  const methods =
    overview?.meta?.methods?.length ? [...overview.meta.methods] : [...scaleIds];
  const defaultMethod = overviewDefaultScale();

  const scaleChart = (() => {
    const rows = scaleMovementSource();
    return rows.length ? buildScaleMovementChart(rows) : null;
  })();

  // Both methods are built here, once, at build time. The island only chooses
  // a block; it never computes a score, a rank or a rounding.
  const panes: Record<string, PaneModel[]> = {};
  const fields: Record<string, FieldSource> = {};
  for (const id of methods) {
    const built = buildMethodPanes(id, scaleChart);
    panes[id] = built.panes;
    fields[id] = built.field;
  }

  const field = fields[defaultMethod] ?? fieldSource(defaultMethod);

  return {
    edition: meta.edition,
    source,
    defaultMethod,
    methods,
    field: {
      min: field.min,
      max: field.max,
      median: field.median,
      count: field.values.length,
    },
    panes,
  };
}

