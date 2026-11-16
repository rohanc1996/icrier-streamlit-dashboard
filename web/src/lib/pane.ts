/**
 * `?pane=` is the carousel's shareable state, following the same convention as
 * `?scale=` on the rankings page: the URL is the source of truth, the default
 * is never written, and changes use `replaceState`.
 */

export function readPaneParam(search: string, count: number, fallback = 1): number {
  const value = Number(new URLSearchParams(search).get('pane'));
  if (!Number.isInteger(value) || value < 1 || value > count) return fallback;
  return value;
}

export function writePaneParam(url: URL, pane: number, fallback = 1): URL {
  if (pane === fallback) url.searchParams.delete('pane');
  else url.searchParams.set('pane', String(pane));
  return url;
}

export function paneAnnouncement(pane: number, count: number, title: string): string {
  return `Pane ${pane} of ${count}: ${title}`;
}
