/** Scaling-method helpers. The active method is UI state carried in the URL. */

export const METHOD_LABELS: Record<string, string> = {
  full_minmax: 'Full-range min–max',
  z: 'Z-score',
};

export const METHOD_SHORT_LABELS: Record<string, string> = {
  full_minmax: 'Min–max',
  z: 'Z-score',
};

export const SCALE_EVENT = 'chips:scale';

export function methodLabel(id: string): string {
  return METHOD_LABELS[id] ?? id;
}

export function methodShortLabel(id: string): string {
  return METHOD_SHORT_LABELS[id] ?? id;
}

/** Reads `?scale=` and falls back unless it names a method the data has. */
export function readScaleParam(
  search: string,
  ids: string[],
  fallback: string,
): string {
  const value = new URLSearchParams(search).get('scale');
  return value && ids.includes(value) ? value : fallback;
}

/** Keeps the chosen scale on links out of the rankings table. */
export function withScale(href: string, scale: string, defaultScale: string): string {
  if (!scale || scale === defaultScale) return href;
  const glue = href.includes('?') ? '&' : '?';
  return `${href}${glue}scale=${encodeURIComponent(scale)}`;
}
