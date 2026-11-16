/**
 * Which countries get a flag, shared by the build, the flag-fetch script and
 * the verifier.
 *
 * The flagged set is derived from the scores every time — never written down as
 * an ISO list — so a change of method, or a new edition, moves the flags
 * without a code edit. Keeping the sort rule here means the sprite, the panes
 * and the checks cannot drift apart.
 */

/** Panes 1, 7 and 8 draw the ten best scores as flags. */
export const FLAG_COUNT = 10;

/** Pane 2 draws all fifteen rows as flags. */
export const TOP15_COUNT = 15;

/**
 * iso3 codes of the best `count` scores, best first.
 *
 * Ties break on the exporter's rank and then on ISO-3, so the set is stable
 * between builds.
 */
export function topByScoreIso3s(values, count) {
  return [...(values ?? [])]
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.rank - b.rank ||
        String(a.iso3).localeCompare(String(b.iso3)),
    )
    .slice(0, count)
    .map((row) => row.iso3);
}

/**
 * Every flag one method's panes can draw: the top 15 by score (which covers the
 * top 10 in panes 1, 7 and 8) unioned with the top-15 list pane 2 rows are
 * built from. The two are normally the same countries; the union makes the
 * sprite right even if an edition's rank list and score order disagree.
 */
export function methodFlagIso3s(fieldValues, top15Rows) {
  return [
    ...new Set([
      ...topByScoreIso3s(fieldValues, TOP15_COUNT),
      ...(top15Rows ?? []).map((row) => row.iso3),
    ]),
  ];
}

/** The whole page's sprite set: the union across both scaling methods. */
export function pageFlagIso3s(methods) {
  const codes = new Set();
  for (const id of Object.keys(methods ?? {})) {
    for (const iso3 of methodFlagIso3s(
      methods[id]?.field?.values,
      methods[id]?.top15,
    )) {
      codes.add(iso3);
    }
  }
  return [...codes].sort();
}
