import { useState } from 'react';
import type { RankBarRow } from '../lib/site';

interface RankBarsProps {
  rows: RankBarRow[];
  max: number;
  selected: Set<string> | null;
  compare: string[];
  label: string;
}

const OPTIONS = [
  { value: 'all', label: 'All countries' },
  { value: '25', label: 'Top 25' },
  { value: '10', label: 'Top 10' },
];

/**
 * Pane 2: every scored country on one shared score axis. The list is filtered
 * by the country grouping and by an explicit "show" control — it is never cut
 * silently. Rows keep their published rank.
 */
export default function RankBars({ rows, max, selected, compare, label }: RankBarsProps) {
  const [topN, setTopN] = useState('all');
  const filtered = selected ? rows.filter((row) => selected.has(row.iso3)) : rows;
  const shown = topN === 'all' ? filtered : filtered.slice(0, Number(topN));
  const compareSet = new Set(compare);

  return (
    <div className="rank-bars">
      <div className="pane-control">
        <label htmlFor="rank-bar-count">Show</label>
        <select
          id="rank-bar-count"
          value={topN}
          onChange={(event) => setTopN(event.target.value)}
        >
          {OPTIONS.map((option) => (
            <option value={option.value} key={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span className="micro hint">
          {shown.length} of {filtered.length} {label.toLowerCase()}
        </span>
      </div>

      <ol className="rank-bars__list" tabIndex={0} aria-label="Ranked countries, scrollable">
        {shown.map((row) => (
          <li
            className={`rank-bars__row${compareSet.has(row.iso3) ? ' is-compared' : ''}`}
            key={row.iso3}
            data-rank-bar={row.iso3}
          >
            <span className="rank-bars__rank">{row.rank}</span>
            <span className="rank-bars__name" title={row.label}>
              {row.label}
            </span>
            <svg className="rank-bars__track" width="100%" height="16" aria-hidden="true">
              <rect
                className="rank-bars__bar"
                x="0"
                y="2"
                width={`${row.pct}%`}
                height="12"
                rx="1"
              />
            </svg>
            <span className="rank-bars__value">{row.scoreText}</span>
          </li>
        ))}
      </ol>
      <p className="micro hint">
        Score axis 0–{max}. Ranks are positions in the published field, not within the
        selected group.
      </p>
    </div>
  );
}
