/**
 * Types shared by the build-time overview builder (`lib/overview.ts`) and the
 * React island that renders it. Everything crossing that boundary must be
 * serialisable: Astro prerenders the island to HTML, then hydrates it.
 */

export interface OverviewMetaJson {
  edition: string;
  generated?: string;
  methods?: string[];
  defaultMethod?: string;
  countries?: number;
  gdpYear?: number;
  gdpSource?: string;
}

export interface OverviewCountryJson {
  iso3: string;
  country: string;
  shortName?: string;
  score: number;
  rank: number;
}

export interface OverviewPillarJson {
  id: string;
  score: number;
  weight?: number;
  contribution?: number;
  rank?: number;
  of?: number;
}

/** Rank correlation between CHIPS score and GDP (pane 7's caption). */
export interface OverviewCorrelationJson {
  pearson: number;
  spearman: number;
  pearsonExTop2?: number;
  spearmanExTop2?: number;
  n?: number;
}

export interface OverviewCompositionJson {
  iso3: string;
  country: string;
  rank: number;
  score: number;
  pillars: OverviewPillarJson[];
}

export interface OverviewIndiaJson {
  iso3: string;
  country: string;
  rank: number;
  score: number;
  pillars: OverviewPillarJson[];
  /** The exporter names the strongest and weakest pillar as objects. */
  best?: { id: string; rank: number };
  worst?: { id: string; rank: number };
}

export interface OverviewMovementJson {
  years: Array<string | number>;
  countries: Array<{
    iso3: string;
    country: string;
    ranks: Record<string, number | null>;
    /** Per-edition composite, 0–1. Present in the method-split payload. */
    scores?: Record<string, number | null>;
  }>;
}

export interface OverviewSizeJson {
  iso3: string;
  country: string;
  score: number;
  rank: number;
  gdp: number;
  gdpPerCapita?: number | null;
}

export interface OverviewCoverageJson {
  iso3: string;
  country: string;
  score: number;
  rank: number;
  coverage: number;
  indicatorsPresent: number;
  indicatorsTotal: number;
}

/**
 * One scaling method's slice of the overview payload. Pane 6 is the exception:
 * it compares the methods, so it lives at the top level, outside `methods{}`.
 */
export interface OverviewMethodJson {
  field: {
    median: number;
    min: number;
    max: number;
    values: OverviewCountryJson[];
  };
  top15: OverviewCountryJson[];
  composition?: OverviewCompositionJson[];
  india?: OverviewIndiaJson;
  movement?: OverviewMovementJson;
  sizeVsScore?: OverviewSizeJson[];
  coverage?: OverviewCoverageJson[];
  correlation?: OverviewCorrelationJson;
}

export interface OverviewJson {
  meta: OverviewMetaJson;
  methods: Record<string, OverviewMethodJson>;
  scaleMovement?: {
    pairs?: string[];
    movers: Array<{
      iso3: string;
      country: string;
      rankFull: number;
      rankZ: number;
      delta: number;
    }>;
  };
}

/* -------- the serialisable view model handed to the carousel -------- */

export interface FieldPointModel {
  iso3: string;
  label: string;
  /** Score on the 0–1 export scale. */
  score: number;
  rank: number;
  /** Horizontal position as a percentage of the plot width. */
  xPct: number;
  /** Vertical centre in SVG user units (px). */
  cy: number;
  isIndia: boolean;
}

export interface FieldChartModel {
  kind: 'field';
  points: FieldPointModel[];
  medianPct: number;
  medianLabel: string;
  height: number;
  axisY: number;
  ticks: Array<{ pct: number; label: string }>;
  ariaLabel: string;
}

export interface Top15RowModel {
  iso3: string;
  label: string;
  score: number;
  rank: number;
  /** Percentage of the shared 0–70 score axis. */
  pct: number;
  scoreText: string;
  isTop3: boolean;
}

export interface Top15ChartModel {
  kind: 'top15';
  rows: Top15RowModel[];
  spanFrom: string;
  spanTo: string;
  ariaLabel: string;
}

/* -------- pane 3: weighted composition -------- */

export interface CompositionSegmentModel {
  id: string;
  /** `composition[].pillars[].contribution`, untouched: score × weight. */
  contribution: number;
  /** Left edge and width as a percentage of the shared track. */
  startPct: number;
  widthPct: number;
  /** The same contribution on the 0–100 scale, to 2 decimals. */
  text: string;
}

export interface CompositionRowModel {
  iso3: string;
  label: string;
  rank: number;
  /** Sum of the five contributions; equals the composite before rounding. */
  total: number;
  totalText: string;
  segments: CompositionSegmentModel[];
}

export interface CompositionChartModel {
  kind: 'composition';
  rows: CompositionRowModel[];
  /** Framework order, so a pillar keeps its position down the stack. */
  pillarOrder: string[];
  legend: Array<{ id: string; label: string; weightText: string }>;
  ticks: Array<{ pct: number; label: string }>;
  ariaLabel: string;
}

/* -------- pane 4: India's pillar ranks inside the field -------- */

export interface VerdictPointModel {
  /** Rank within the pillar, 1 = best. */
  rank: number;
  /** Horizontal position as a percentage of the plot width. */
  xPct: number;
  /** Vertical offset from the row centre, in px, spreading ties. */
  dy: number;
}

export interface VerdictRowModel {
  id: string;
  scoreText: string;
  rank: number;
  of: number;
  /** All countries' ranks in this pillar, one point each. */
  points: VerdictPointModel[];
  indiaXPct: number;
  best: number;
  median: number;
  worst: number;
}

export interface IndiaChartModel {
  kind: 'india';
  rows: VerdictRowModel[];
  ticks: Array<{ pct: number; label: string }>;
  rowHeight: number;
  height: number;
  best: { id: string; rank: number };
  worst: { id: string; rank: number };
  of: number;
  ariaLabel: string;
}

/* -------- pane 5: score movement across editions -------- */

export interface MovementPointModel {
  year: number;
  /** Score on the 0–1 export scale, from the comparison series. */
  score: number;
  xPct: number;
}

export interface MovementRowModel {
  iso3: string;
  label: string;
  highlighted: boolean;
  points: MovementPointModel[];
  /** One `<line>` per run of consecutive scored years. */
  segments: Array<{ from: MovementPointModel; to: MovementPointModel }>;
  /** Last available score − first available score, on the 0–1 scale. */
  deltaPoints: number | null;
  /** Signed points, one decimal: "+1.2", "−1.0", "0.0". */
  deltaText: string;
  /** The last available score, 2 dp on the 0–100 scale. */
  lastScoreText: string;
  /** Last available rank − first available rank (table only). */
  rankChange: number | null;
  /** Rank per edition, keyed by year as a string (table only). */
  ranks: Record<string, number | null>;
}

export interface MovementChartModel {
  kind: 'movement';
  years: number[];
  rows: MovementRowModel[];
  /** 0–100 score axis, fixed so every row is comparable. */
  ticks: Array<{ pct: number; label: string }>;
  count: number;
  total: number;
  caveat: string;
  height: number;
  ariaLabel: string;
}

/* -------- pane 6: rank movement between scaling methods -------- */

export interface ScaleMovementRowModel {
  iso3: string;
  label: string;
  rankFull: number;
  rankZ: number;
  /** rankZ − rankFull: negative means the z-score ranks the country better. */
  delta: number;
  deltaText: string;
  /** "55 → 36", printed beside the bar. */
  rankText: string;
  /** Bar geometry as a percentage of the track, measured from the zero line. */
  startPct: number;
  widthPct: number;
  side: 'better' | 'worse';
}

export interface ScaleMovementChartModel {
  kind: 'scaleMovement';
  rows: ScaleMovementRowModel[];
  ticks: Array<{ pct: number; label: string }>;
  /** All countries with both ranks, and those whose rank actually changes. */
  total: number;
  changed: number;
  headline: string;
  gainLabel: string;
  lossLabel: string;
  ariaLabel: string;
}

/* -------- panes 7–8: scatter plots with a fixed pixel height -------- */

export interface ScatterPointModel {
  iso3: string;
  label: string;
  /** Score on the 0–1 export scale. */
  score: number;
  /** GDP in current US dollars (pane 7 only). */
  gdp?: number;
  /** Data coverage as a fraction (pane 8 only). */
  coverage?: number;
  xPct: number;
  y: number;
  /** Pane 8: coverage is below the 80% line. */
  belowThreshold?: boolean;
  /** Present only for the few points the chart names. */
  labelXPct?: number;
  labelY?: number;
  labelAnchor?: 'start' | 'middle' | 'end';
}

export interface ScatterChartModel {
  kind: 'sizeScore' | 'coverage';
  points: ScatterPointModel[];
  xTicks: Array<{ pct: number; label: string }>;
  yTicks: Array<{ y: number; label: string }>;
  height: number;
  plotLeftPct: number;
  plotRightPct: number;
  /** Pane 8: where the 80% rule sits, as a percentage of the plot width. */
  thresholdPct?: number;
  belowThreshold?: number;
  unscoredCells?: number;
  ariaLabel: string;
}

export interface PlaceholderChartModel {
  kind: 'placeholder';
  /** Honest line shown in the chart slot. Never carries a number. */
  note: string;
  /** Extra line for panes that already know their panel shape. */
  detail?: string;
}

export type PaneChartModel =
  | FieldChartModel
  | Top15ChartModel
  | CompositionChartModel
  | IndiaChartModel
  | MovementChartModel
  | ScaleMovementChartModel
  | ScatterChartModel
  | PlaceholderChartModel;

export interface PaneTableModel {
  caption: string;
  columns: string[];
  rows: string[][];
  note: string;
  /** Column indices that hold numbers; right-aligned. Defaults to first/last. */
  numericColumns?: number[];
}

export interface PaneModel {
  number: number;
  title: string;
  /** One line: what this shows. */
  what: string;
  /** Optional longer caption under the chart. */
  caption?: string;
  chart: PaneChartModel;
  /** Real table for built panes; null for the placeholders. */
  table: PaneTableModel | null;
  /** Honest fallback copy for panes whose chart is not built yet. */
  tableFallback: string | null;
  methodNote: string;
}

export interface OverviewView {
  edition: string;
  source: 'overview.json' | 'chips.json';
  /** The method the site opens on, read from `meta.defaultMethod`. */
  defaultMethod: string;
  /** Method ids in payload order; the toggle renders in this order. */
  methods: string[];
  /** Field summary for the default method (the page head prints it). */
  field: {
    min: number;
    max: number;
    median: number;
    count: number;
  };
  /** One eight-pane block per scaling method. Pane 6 is identical in each. */
  panes: Record<string, PaneModel[]>;
}
