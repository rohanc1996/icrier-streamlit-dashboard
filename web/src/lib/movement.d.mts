export interface MovementPoint {
  year: number;
  rank: number | null;
}

export interface MovementRun {
  fromYear: number;
  toYear: number;
  fromRank: number;
  toRank: number;
}

export function movementPoints(
  years: Array<number | string>,
  ranks: Record<string, number | null | undefined>,
): MovementPoint[];

export function movementRuns(
  years: Array<number | string>,
  ranks: Record<string, number | null | undefined>,
): MovementRun[];

export function movementChange(
  years: Array<number | string>,
  ranks: Record<string, number | null | undefined>,
): number | null;
