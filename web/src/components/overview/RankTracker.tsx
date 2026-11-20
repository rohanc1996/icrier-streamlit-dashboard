import type { TrackerBlock } from '../lib/site';

interface RankTrackerProps {
  block: TrackerBlock;
  selected: Set<string> | null;
  compare: string[];
  /** Countries the latest edition carries, for the "of N" caveat. */
  total: number;
}

/**
 * Pane 5: rank only, one row per country present in every selected edition.
 * The subset is re-ranked within itself each year so the lines are comparable.
 * Scores are deliberately absent: the methodology, indicators and weights
 * changed between editions, so a score is not a like-for-like series.
 */
export default function RankTracker({ block, selected, compare, total }: RankTrackerProps) {
  const years = block.years;
  const rows = selected
    ? block.countries.filter((row) => selected.has(row.iso3))
    : block.countries;
  const compareSet = new Set(compare);
  const maxRank = Math.max(1, block.count);

  const movers = [...rows]
    .filter((row) => row.ranks[String(years[0])] !== undefined)
    .sort(
      (a, b) =>
        Math.abs(
          b.ranks[String(years[years.length - 1])] - b.ranks[String(years[0])],
        ) -
          Math.abs(
            a.ranks[String(years[years.length - 1])] - a.ranks[String(years[0])],
          ) || a.country.localeCompare(b.country),
    )
    .slice(0, 6);

  const width = 700;
  const height = 220;
  const x = (index: number) => 40 + (index / Math.max(1, years.length - 1)) * (width - 170);
  const y = (rank: number) => 22 + ((rank - 1) / Math.max(1, maxRank - 1)) * 140;

  // Labels are pushed apart vertically so six movers never overlap at the
  // right-hand end; the line still ends on the exact rank.
  const labelY = new Map<string, number>();
  let cursor = Number.NEGATIVE_INFINITY;
  for (const row of [...movers].sort(
    (a, b) =>
      a.ranks[String(years[years.length - 1])] - b.ranks[String(years[years.length - 1])],
  )) {
    const target = y(row.ranks[String(years[years.length - 1])]);
    const placed = Math.max(target, cursor + 13);
    labelY.set(row.iso3, placed);
    cursor = placed;
  }

  return (
    <div className="tracker">
      <p className="pane__callout">
        {block.count} countries are scored in every selected edition
        {selected ? ` (${rows.length} in this group)` : ''}. The method, indicators and
        weights changed between editions, so only relative position within a year is
        comparable.
      </p>

      <div className="tracker__chart">
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`Rank paths for the six largest movers between ${years.join(' and ')}. Lower is better.`}
        >
          <line className="tracker__axis" x1="30" y1={y(1)} x2={width - 10} y2={y(1)} />
          <line
            className="tracker__axis"
            x1="30"
            y1={y(maxRank)}
            x2={width - 10}
            y2={y(maxRank)}
          />
          <text className="chart__tick-label" x="6" y={y(1) + 4}>
            1
          </text>
          <text className="chart__tick-label" x="6" y={y(maxRank) + 4}>
            {maxRank}
          </text>
          {years.map((year, index) => (
            <text
              key={year}
              className="chart__tick-label"
              x={x(index)}
              y={height - 6}
              textAnchor="middle"
            >
              {year}
            </text>
          ))}
          {movers.map((row) => {
            const points = years
              .map((year, index) => ({ index, rank: row.ranks[String(year)] }))
              .filter((point) => point.rank !== undefined);
            const path = points
              .map((point, i) => `${i === 0 ? 'M' : 'L'} ${x(point.index)} ${y(point.rank)}`)
              .join(' ');
            return (
              <g key={row.iso3} data-tracker={row.iso3}>
                <path className="tracker__line" d={path} />
                {points.map((point) => (
                  <circle
                    key={point.index}
                    className="tracker__dot"
                    cx={x(point.index)}
                    cy={y(point.rank)}
                    r="3"
                  />
                ))}
                <text
                  className={`chart__label${compareSet.has(row.iso3) ? ' is-compared' : ''}`}
                  x={x(years.length - 1) + 4}
                  y={(labelY.get(row.iso3) ?? y(row.ranks[String(years[years.length - 1])])) + 4}
                  textAnchor="start"
                >
                  {row.shortName || row.country}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="tracker__table-wrap" tabIndex={0} role="region" aria-label="Rank tracker table, scrollable">
        <table className="data-table tracker__table">
          <caption className="micro hint">
            Ranks only. Each row is one country, re-ranked within this {block.count}-country
            subset in each edition.
          </caption>
          <thead>
            <tr>
              <th scope="col">Country</th>
              {years.map((year) => (
                <th scope="col" key={year}>
                  {year} rank
                </th>
              ))}
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const first = row.ranks[String(years[0])];
              const last = row.ranks[String(years[years.length - 1])];
              const change = last - first;
              return (
                <tr key={row.iso3} className={compareSet.has(row.iso3) ? 'is-compared' : undefined}>
                  <th scope="row">{row.shortName || row.country}</th>
                  {years.map((year) => (
                    <td key={year}>{row.ranks[String(year)] ?? '—'}</td>
                  ))}
                  <td>
                    {change === 0 ? '0' : change > 0 ? `−${change}` : `+${Math.abs(change)}`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="micro hint">
        A positive change is a higher position than the first selected edition. Pool:
        {` ${total}`} countries in the latest edition.
      </p>
    </div>
  );
}
