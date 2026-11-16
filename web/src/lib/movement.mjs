/**
 * The movement geometry both the build and the verifier use.
 *
 * `ranks` is keyed by the year as a string and may be `null` when a country
 * was not scored in that edition. Despite the name it is any per-year series:
 * pane 5 passes CHIPS scores through these helpers. A null is a gap: no
 * segment may start or end on it, so a line never claims a movement the data
 * does not show.
 */

/** Present ranks only, in year order. */
export function movementPoints(years, ranks) {
  const points = [];
  for (const year of years) {
    const value = ranks[String(year)];
    const rank = typeof value === 'number' && Number.isFinite(value) ? value : null;
    points.push({ year: Number(year), rank });
  }
  return points;
}

/**
 * Consecutive scored years as drawable segments. A run is broken by a null,
 * so `[5, null, 9]` yields no segment at all, while `[5, 6, null]` yields one.
 */
export function movementRuns(years, ranks) {
  const runs = [];
  let previous = null;
  for (const point of movementPoints(years, ranks)) {
    if (point.rank === null) {
      previous = null;
      continue;
    }
    if (previous) {
      runs.push({
        fromYear: previous.year,
        toYear: point.year,
        fromRank: previous.rank,
        toRank: point.rank,
      });
    }
    previous = point;
  }
  return runs;
}

/**
 * Change across the whole span: last available rank minus first available
 * rank. Null when fewer than two years carry a rank, or when no rank exists.
 */
export function movementChange(years, ranks) {
  const present = movementPoints(years, ranks).filter((point) => point.rank !== null);
  if (present.length < 2) return null;
  return present[present.length - 1].rank - present[0].rank;
}
