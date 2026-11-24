import { useMemo, useState } from 'react';
import type { TrackerBlock } from '../lib/site';

interface RankTrackerProps {
  block: TrackerBlock;
  selected: Set<string> | null;
  compare: string[];
  /** Countries the latest edition carries, for the "of N" caveat. */
  total: number;
}

type SortMode = 'latest' | 'change';

const WIDTH = 900;
const LEFT = 56;
const RIGHT = 230;
const TOP = 26;

/**
 * Pane 5: every selected edition on one rank ladder.
 *
 * Scores are deliberately absent: the method, indicators and weights changed
 * between editions, so only position within a year is comparable. Every country
 * is drawn as a path and named once, at the right-hand edge, at its rank in the
 * last selected year. The lines carry the year-to-year movement; a short leader
 * connects a displaced label back to its final dot. The table below carries
 * every year's rank and the move between them.
 */
export default function RankTracker({ block, selected, compare, total }: RankTrackerProps) {
  const years = block.years;
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

  /** Largest movers on any transition: these keep the stronger line. */
  const movers = useMemo(() => {
    const codes = new Set<string>();
    for (const { from, to } of transitions) {
      const list = [...rows]
        .map((row) => ({
          iso3: row.iso3,
          delta: Math.abs((row.ranks[String(to)] ?? 0) - (row.ranks[String(from)] ?? 0)),
        }))
        .filter((row) => row.delta > 0)
        .sort((a, b) => b.delta - a.delta || a.iso3.localeCompare(b.iso3))
        .slice(0, 4);
      for (const mover of list) codes.add(mover.iso3);
    }
    return codes;
  }, [rows, transitions]);

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

  // A 19-country group needs ~360px; the 38-country view grows so every label
  // fits without overlap.
  const height = Math.max(360, rows.length * 16 + 64);
  const bottom = height - 52;
  const x = (index: number) =>
    years.length === 1
      ? LEFT + (WIDTH - LEFT - RIGHT) / 2
      : LEFT + (index / (years.length - 1)) * (WIDTH - LEFT - RIGHT);
  const y = (rank: number) => TOP + ((rank - 1) / Math.max(1, maxRank - 1)) * (bottom - TOP);
  const lastX = x(years.length - 1);

  /** One label per country at the last year, pushed apart where ranks cluster. */
  const labels = useMemo(() => {
    const placed = new Map<string, number>();
    let cursor = Number.NEGATIVE_INFINITY;
    const ordered = rows
      .filter((row) => row.ranks[String(lastYear)] !== undefined)
      .sort(
        (a, b) =>
          a.ranks[String(lastYear)] - b.ranks[String(lastYear)] ||
          a.country.localeCompare(b.country),
      );
    for (const row of ordered) {
      const value = Math.max(y(row.ranks[String(lastYear)]), cursor + 14);
      placed.set(row.iso3, value);
      cursor = value;
    }
    return placed;
  }, [rows, lastYear, maxRank, height]);

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

      <div className="tracker__chart">
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 ${WIDTH} ${height}`}
          role="img"
          aria-label={`Rank ladder for ${rows.length} countries across ${years.join(
            ', ',
          )}. Rank 1 is best. Every country is labelled at ${lastYear}, its last selected year.`}
        >
          {[1, Math.round(maxRank / 2), maxRank].map((rank) => (
            <g key={rank}>
              <line
                className="tracker__grid"
                x1={LEFT}
                y1={y(rank)}
                x2={lastX}
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
              y={height - 10}
              textAnchor="middle"
            >
              {year}
            </text>
          ))}

          {rows.map((row) => {
            const isCompared = compareSet.has(row.iso3);
            const isMover = movers.has(row.iso3);
            const points = years
              .map((year, index) => ({ index, rank: row.ranks[String(year)] }))
              .filter((point) => point.rank !== undefined);
            const path = points
              .map(
                (point, i) =>
                  `${i === 0 ? 'M' : 'L'} ${x(point.index)} ${y(point.rank as number)}`,
              )
              .join(' ');
            const trail = years
              .map((year) => `${year}: ${row.ranks[String(year)] ?? '—'}`)
              .join(', ');
            const labelY = labels.get(row.iso3);
            return (
              <g
                key={row.iso3}
                className={`tracker__country${isMover ? ' is-highlighted' : ''}${
                  isCompared ? ' is-compared' : ''
                }`}
                data-tracker={row.iso3}
              >
                <title>{`${row.shortName || row.country} — ${trail}`}</title>
                <path className="tracker__line" d={path} />
                {points.map((point) => (
                  <circle
                    key={point.index}
                    className="tracker__dot"
                    cx={x(point.index)}
                    cy={y(point.rank as number)}
                    r={isCompared || isMover ? 3.2 : 2}
                  />
                ))}
                {labelY !== undefined && (
                  <path
                    className="tracker__leader"
                    d={`M ${lastX + 2} ${y(row.ranks[String(lastYear)])} L ${
                      lastX + 8
                    } ${labelY} L ${lastX + 11} ${labelY}`}
                  />
                )}
              </g>
            );
          })}

          {rows.map((row) => {
            const labelY = labels.get(row.iso3);
            const rank = row.ranks[String(lastYear)];
            if (labelY === undefined || rank === undefined) return null;
            const isCompared = compareSet.has(row.iso3);
            return (
              <text
                key={`${row.iso3}-label`}
                className={`tracker__label${isCompared ? ' is-compared' : ''}`}
                x={lastX + 12}
                y={labelY + 4}
                textAnchor="start"
              >
                {(row.shortName || row.country).slice(0, 20)} · {rank}
              </text>
            );
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
        <span className="micro hint">
          Every country is drawn and named at {lastYear}; the table carries every
          year.
        </span>
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
