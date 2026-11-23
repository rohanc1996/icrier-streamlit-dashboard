import { useMemo, useState } from 'react';
import type { TrackerBlock } from '../lib/site';

interface RankTrackerProps {
  block: TrackerBlock;
  selected: Set<string> | null;
  compare: string[];
  /** Countries the latest edition carries, for the "of N" caveat. */
  total: number;
}

type HighlightMode = 'movers' | 'compare' | 'none';
type SortMode = 'latest' | 'change';

const WIDTH = 900;
const HEIGHT = 320;
const LEFT = 56;
const RIGHT = 200;
const TOP = 26;
const BOTTOM = 272;

/**
 * Pane 5: every selected edition on one rank ladder.
 *
 * Scores are deliberately absent: the method, indicators and weights changed
 * between editions, so only position within a year is comparable. All
 * countries in the group are drawn as faint paths; the largest movers on each
 * transition and the comparison countries are labelled at *every* year, so a
 * reader can follow the shift rather than infer it from one end point. The
 * table below carries every country and every year.
 */
export default function RankTracker({ block, selected, compare, total }: RankTrackerProps) {
  const years = block.years;
  const [highlight, setHighlight] = useState<HighlightMode>('movers');
  const [sortMode, setSortMode] = useState<SortMode>('latest');

  const rows = useMemo(
    () => (selected ? block.countries.filter((row) => selected.has(row.iso3)) : block.countries),
    [block.countries, selected],
  );
  const compareSet = useMemo(() => new Set(compare), [compare]);
  const maxRank = Math.max(1, block.count);

  const transitions = years.slice(1).map((year, index) => ({
    from: years[index],
    to: year,
  }));

  const lastYear = years[years.length - 1];
  const firstYear = years[0];

  /** The largest movers on any transition, plus the comparison countries. */
  const highlighted = useMemo(() => {
    if (highlight === 'none') return new Set<string>();
    if (highlight === 'compare') return new Set(compare);
    const codes = new Set<string>(compare);
    for (const { from, to } of transitions) {
      const movers = [...rows]
        .map((row) => ({
          iso3: row.iso3,
          delta: Math.abs((row.ranks[String(to)] ?? 0) - (row.ranks[String(from)] ?? 0)),
        }))
        .filter((row) => row.delta > 0)
        .sort((a, b) => b.delta - a.delta || a.iso3.localeCompare(b.iso3))
        .slice(0, 4);
      for (const mover of movers) codes.add(mover.iso3);
    }
    return codes;
  }, [compare, highlight, rows, transitions]);

  const sorted = useMemo(() => {
    const list = [...rows];
    if (sortMode === 'change') {
      list.sort(
        (a, b) =>
          Math.abs((b.ranks[String(lastYear)] ?? 0) - (b.ranks[String(firstYear)] ?? 0)) -
            Math.abs((a.ranks[String(lastYear)] ?? 0) - (a.ranks[String(firstYear)] ?? 0)) ||
          (a.ranks[String(lastYear)] ?? 0) - (b.ranks[String(lastYear)] ?? 0),
      );
    } else {
      list.sort(
        (a, b) =>
          (a.ranks[String(lastYear)] ?? 0) - (b.ranks[String(lastYear)] ?? 0) ||
          a.country.localeCompare(b.country),
      );
    }
    return list;
  }, [rows, sortMode, firstYear, lastYear]);

  const x = (index: number) =>
    years.length === 1
      ? LEFT + (WIDTH - LEFT - RIGHT) / 2
      : LEFT + (index / (years.length - 1)) * (WIDTH - LEFT - RIGHT);
  const y = (rank: number) => TOP + ((rank - 1) / Math.max(1, maxRank - 1)) * (BOTTOM - TOP);

  // One label column per year; push labels apart so the highlighted group is
  // readable at every edition, not only at the last one.
  const labelY = useMemo(() => {
    const placed: Record<string, Map<string, number>> = {};
    for (const [index, year] of years.entries()) {
      const column = new Map<string, number>();
      let cursor = Number.NEGATIVE_INFINITY;
      const entries = rows
        .filter((row) => highlighted.has(row.iso3))
        .sort((a, b) => (a.ranks[String(year)] ?? 0) - (b.ranks[String(year)] ?? 0));
      for (const row of entries) {
        const target = y(row.ranks[String(year)] ?? maxRank);
        const value = Math.max(target, cursor + 13);
        column.set(row.iso3, value);
        cursor = value;
      }
      placed[String(year)] = column;
    }
    return placed;
  }, [highlighted, rows, years, maxRank]);

  const latestTransition = transitions[transitions.length - 1];
  const changedLatest = latestTransition
    ? rows.filter(
        (row) =>
          row.ranks[String(latestTransition.from)] !== row.ranks[String(latestTransition.to)],
      ).length
    : 0;
  const biggest = latestTransition
    ? [...rows]
        .map((row) => ({
          row,
          delta:
            (row.ranks[String(latestTransition.to)] ?? 0) -
            (row.ranks[String(latestTransition.from)] ?? 0),
        }))
        .sort(
          (a, b) =>
            Math.abs(b.delta) - Math.abs(a.delta) ||
            a.row.country.localeCompare(b.row.country),
        )[0]
    : null;

  return (
    <div className="tracker">
      <p className="pane__callout">
        {block.count} countries are scored in every selected edition
        {selected ? ` (${rows.length} in this group)` : ''}. From{' '}
        {latestTransition?.from ?? firstYear} to {latestTransition?.to ?? lastYear},{' '}
        <strong>
          {changedLatest} of {rows.length}
        </strong>{' '}
        changed rank
        {biggest && biggest.delta !== 0 ? (
          <>
            ; the largest move was {biggest.row.shortName || biggest.row.country},{' '}
            {biggest.delta < 0
              ? `up ${Math.abs(biggest.delta)} place${Math.abs(biggest.delta) === 1 ? '' : 's'}`
              : `down ${biggest.delta} place${biggest.delta === 1 ? '' : 's'}`}
          </>
        ) : null}
        . The method, indicators and weights changed between editions, so only
        relative position within a year is comparable.
      </p>

      <div className="tracker__controls pane-control">
        <label htmlFor="tracker-highlight">Label</label>
        <select
          id="tracker-highlight"
          value={highlight}
          onChange={(event) => setHighlight(event.target.value as HighlightMode)}
        >
          <option value="movers">Largest movers + comparison</option>
          <option value="compare">Comparison countries only</option>
          <option value="none">No labels</option>
        </select>
        <span className="micro hint">
          All {rows.length} countries are drawn; every rank is in the table.
        </span>
      </div>

      <div className="tracker__chart">
        <svg
          width="100%"
          height={HEIGHT}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`Rank ladder for ${rows.length} countries across ${years.join(
            ', ',
          )}. Rank 1 is best. Faint lines are all countries; highlighted lines are the largest movers and the comparison countries.`}
        >
          {[1, Math.round(maxRank / 2), maxRank].map((rank) => (
            <g key={rank}>
              <line
                className="tracker__grid"
                x1={LEFT}
                y1={y(rank)}
                x2={WIDTH - RIGHT + 120}
                y2={y(rank)}
              />
              <text className="chart__tick-label" x={LEFT - 8} y={y(rank) + 4} textAnchor="end">
                {rank}
              </text>
            </g>
          ))}
          {years.map((year, index) => (
            <text
              key={year}
              className="tracker__year"
              x={x(index)}
              y={HEIGHT - 12}
              textAnchor="middle"
            >
              {year}
            </text>
          ))}

          {rows.map((row) => {
            const isHighlighted = highlighted.has(row.iso3);
            const isCompared = compareSet.has(row.iso3);
            const points = years
              .map((year, index) => ({ index, rank: row.ranks[String(year)] }))
              .filter((point) => point.rank !== undefined);
            const path = points
              .map((point, i) => `${i === 0 ? 'M' : 'L'} ${x(point.index)} ${y(point.rank as number)}`)
              .join(' ');
            const label = years
              .map((year) => `${year}: ${row.ranks[String(year)] ?? '—'}`)
              .join(', ');
            return (
              <g
                key={row.iso3}
                className={`tracker__country${isHighlighted ? ' is-highlighted' : ''}${
                  isCompared ? ' is-compared' : ''
                }`}
                data-tracker={row.iso3}
                tabIndex={isHighlighted ? 0 : -1}
                role="img"
                aria-label={`${row.shortName || row.country}, ${label}`}
              >
                <title>{`${row.shortName || row.country} — ${label}`}</title>
                <path className="tracker__line" d={path} />
                {points.map((point) => (
                  <circle
                    key={point.index}
                    className="tracker__dot"
                    cx={x(point.index)}
                    cy={y(point.rank as number)}
                    r={isHighlighted ? 3.2 : 2}
                  />
                ))}
              </g>
            );
          })}

          {rows.map((row) => {
            if (!highlighted.has(row.iso3)) return null;
            const isCompared = compareSet.has(row.iso3);
            return years.map((year) => {
              const rank = row.ranks[String(year)];
              if (rank === undefined) return null;
              return (
                <text
                  key={`${row.iso3}-${year}-label`}
                  className={`tracker__label${isCompared ? ' is-compared' : ''}`}
                  x={x(years.indexOf(year)) + 8}
                  y={(labelY[String(year)]?.get(row.iso3) ?? y(rank)) + 4}
                  textAnchor="start"
                >
                  {(row.shortName || row.country).slice(0, 18)} · {rank}
                </text>
              );
            });
          })}
        </svg>
      </div>

      <div className="tracker__controls pane-control">
        <label htmlFor="tracker-sort">Sort table by</label>
        <select
          id="tracker-sort"
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value as SortMode)}
        >
          <option value="latest">Latest rank</option>
          <option value="change">Largest change</option>
        </select>
      </div>

      <div
        className="tracker__table-wrap"
        tabIndex={0}
        role="region"
        aria-label="Rank tracker table, scrollable"
      >
        <table className="data-table tracker__table">
          <caption className="micro hint">
            Ranks only. Each row is one country, re-ranked within this {block.count}-country
            subset in each edition. ▲ is a better position, ▼ a worse one.
          </caption>
          <thead>
            <tr>
              <th scope="col">Country</th>
              {years.map((year, index) => (
                <th scope="col" key={year}>
                  {year} rank
                  {index > 0 && <span className="tracker__th-note"> · change</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => {
              const isCompared = compareSet.has(row.iso3);
              return (
                <tr key={row.iso3} className={isCompared ? 'is-compared' : undefined}>
                  <th scope="row">{row.shortName || row.country}</th>
                  {years.map((year, index) => {
                    const rank = row.ranks[String(year)];
                    const previous = index > 0 ? row.ranks[String(years[index - 1])] : undefined;
                    const delta =
                      index > 0 && previous !== undefined && rank !== undefined
                        ? rank - previous
                        : null;
                    return (
                      <td key={year}>
                        <span className="tracker__rank-cell">{rank ?? '—'}</span>
                        {delta !== null && (
                          <span
                            className={`delta-pill ${
                              delta === 0
                                ? 'delta-pill--none'
                                : delta > 0
                                  ? 'delta-pill--down'
                                  : 'delta-pill--up'
                            }`}
                          >
                            {delta === 0
                              ? '–'
                              : delta > 0
                                ? `▼ ${delta}`
                                : `▲ ${Math.abs(delta)}`}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="micro hint">
        Pool: {total} countries in the latest edition. Ranks are positions in the
        published field, re-ranked within this subset; they are not comparable with a
        rank from a different subset.
      </p>
    </div>
  );
}
