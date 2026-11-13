import type { Pillar } from './types';

/** `HARNESS · AI` → `harness.ai`; URL segment only, never a display name. */
export function slugify(value: string): string {
  return value
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function pillarOpenSlug(pillar: Pillar): string {
  return slugify(pillar.id);
}

export function subPillarOpenSlug(pillar: Pillar, subName: string): string {
  return `${slugify(pillar.id)}.${slugify(subName)}`;
}

export interface OpenTarget {
  pillarId: string;
  /** Full sub-pillar key (`HARNESS · AI`), or null for the pillar level. */
  subKey: string | null;
}

/**
 * Reads `?open=` against the framework. Invalid values are ignored rather
 * than opening an empty panel. SUSTAINABILITY has one sub-pillar and skips
 * that level, so either `?open=sustainability` or
 * `?open=sustainability.sustainability` lands on its indicators.
 */
export function readOpenParam(search: string, pillars: Pillar[]): OpenTarget | null {
  const value = new URLSearchParams(search).get('open');
  if (!value) return null;

  const [pillarPart, ...rest] = value.split('.');
  const pillar = pillars.find((item) => item.id.toLowerCase() === pillarPart.toLowerCase());
  if (!pillar) return null;

  if (pillar.subPillars.length === 1 || rest.length === 0) {
    return { pillarId: pillar.id, subKey: null };
  }

  const subSlug = rest.join('.');
  const sub = pillar.subPillars.find((item) => slugify(item.name) === subSlug);
  return { pillarId: pillar.id, subKey: sub?.key ?? null };
}

/** Writes `open` while leaving `scale` (and anything else) untouched. */
export function writeOpenParam(url: URL, value: string | null): URL {
  if (value) url.searchParams.set('open', value);
  else url.searchParams.delete('open');
  return url;
}
