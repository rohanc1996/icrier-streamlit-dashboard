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

/**
 * The name used when one method is the *comparison* for another: the movement
 * column reads "Rank vs min–max" while z is active and "Rank vs z" while
 * min–max is.
 */
export const MOVEMENT_LABELS: Record<string, string> = {
  full_minmax: 'min–max',
  z: 'z',
};

export function movementLabel(id: string): string {
  return MOVEMENT_LABELS[id] ?? methodShortLabel(id);
}

export function methodLabel(id: string): string {
  return METHOD_LABELS[id] ?? id;
}

export function methodShortLabel(id: string): string {
  return METHOD_SHORT_LABELS[id] ?? id;
}

/**
 * The URL is a reader-facing token, not the export's key. Min–max is published
 * in the payload as `full_minmax`; the address bar says `scale=minmax`.
 */
const URL_TO_METHOD: Record<string, string> = { minmax: 'full_minmax' };
const METHOD_TO_URL: Record<string, string> = { full_minmax: 'minmax' };

export function scaleFromToken(token: string, ids: string[]): string | null {
  const id = URL_TO_METHOD[token] ?? token;
  return ids.includes(id) ? id : null;
}

export function scaleToken(id: string): string {
  return METHOD_TO_URL[id] ?? id;
}

/** Reads `?scale=` and falls back unless it names a method the data has. */
export function readScaleParam(
  search: string,
  ids: string[],
  fallback: string,
): string {
  const value = new URLSearchParams(search).get('scale');
  return (value && scaleFromToken(value, ids)) || fallback;
}

/**
 * Writes `?scale=` with the default left out of the URL, so the default is
 * never spelled out and `?scale=z` normalises to absent. Other parameters
 * (`?pane=`, `?open=`) are preserved.
 */
export function writeScaleParam(url: URL, scale: string, fallback: string): URL {
  if (!scale || scale === fallback) url.searchParams.delete('scale');
  else url.searchParams.set('scale', scaleToken(scale));
  return url;
}

/** The method a comparison is measured against: whichever is not active. */
export function otherScale(ids: string[], active: string): string | null {
  return ids.find((id) => id !== active) ?? null;
}

/** Keeps the chosen scale on links out of the rankings table. */
export function withScale(href: string, scale: string, defaultScale: string): string {
  if (!scale || scale === defaultScale) return href;
  const glue = href.includes('?') ? '&' : '?';
  return `${href}${glue}scale=${encodeURIComponent(scaleToken(scale))}`;
}
