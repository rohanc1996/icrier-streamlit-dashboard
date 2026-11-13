export interface PillarScore {
  score: number | null;
  rank: number | null;
}

export interface SubPillarScore {
  score: number | null;
  /** World rank from the exporter; 1 = best. Null when not scored. */
  rank: number | null;
  status: string;
  reason: string | null;
}

export interface ScoreRow {
  iso3: string;
  iso2?: string;
  country: string;
  shortName: string;
  overall: number;
  rank: number;
  chipsStatus: string;
  coverage: number;
  indicatorsPresent: number;
  indicatorsTotal: number;
  pillarsPresent: number;
  pillars: Record<string, PillarScore>;
  subPillars: Record<string, SubPillarScore>;
}

export interface Leaf {
  name: string;
  column: string;
  label: string;
  higherIsBetter: boolean;
  weightInGroup: number;
  group: string | null;
  groupWeight: number | null;
}

export interface SubPillar {
  key: string;
  name: string;
  pillarId: string;
  weight: number;
  leaves: Leaf[];
}

export interface Pillar {
  id: string;
  weight: number;
  subPillars: SubPillar[];
}

export interface IndicatorRow {
  iso3: string;
  leaf: string;
  label: string;
  pillar: string;
  subPillar: string;
  group: string | null;
  raw: number | null;
  score: number | null;
  status: string;
  reason: string | null;
  rank: number | null;
  of: number;
  effectiveWeight: number;
}

export interface MethodPayload {
  scores: ScoreRow[];
  indicators: IndicatorRow[];
}

export interface ChipsMeta {
  edition: string;
  generated: string;
  methods: string[];
  defaultMethod: string;
  countries: number;
  leaves: number;
  indicatorsLoadable: number;
  excludedFromIndex: Array<{ column: string; reason: string }>;
  [key: string]: unknown;
}

export interface ChipsData {
  meta: ChipsMeta;
  framework: { pillars: Pillar[] };
  methods: Record<string, MethodPayload>;
}

/** Lightweight shape passed to React islands — no indicator payloads. */
export interface PillarLite {
  id: string;
  weight: number;
  subPillarCount: number;
  indicatorCount: number;
}

export interface ScaleScores {
  id: string;
  scores: ScoreRow[];
  median: number;
  min: number;
  max: number;
}

export type SortKey = 'rank' | 'country' | 'score';
export type SortDirection = 'asc' | 'desc';
export interface SortState {
  key: SortKey;
  dir: SortDirection;
}
