import { useMemo, useState } from 'react';
import type { RobustnessRow } from '../lib/site';

type SortKey = 'country' | 'rankFull' | 'rankZ' | 'delta';

interface RobustnessTableProps {
  rows: RobustnessRow[];
  selected: Set<string> | null;
  compare: string[];
}

/**
 * Pane 6: the robustness view, not a leaderboard of shocks. Sorted by the
 * smallest absolute rank difference by default, so the countries whose rank
 * barely moves are the first thing a reader sees. Every column sorts.
 */
export default function RobustnessTable({ rows, selected, compare }: RobustnessTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({
    key: 'delta',
    dir: 'asc',
  });

  const filtered = useMemo(
    () => (selected ? rows.filter((row) => selected.has(row.iso3)) : rows),
    [rows, selected],
  );

  const sorted = useMemo(() => {
    const factor = sort.dir === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      if (sort.key === 'country') {
        return (
          factor * (a.shortName || a.country).localeCompare(b.shortName || b.country, 'en') ||
          a.rankFull - b.rankFull
        );
      }
      const left =
        sort.key === 'delta' ? Math.abs(a.delta) : (a[sort.key] as number);
      const right =
        sort.key === 'delta' ? Math.abs(b.delta) : (b[sort.key] as number);
      return factor * (left - right) || a.rankFull - b.rankFull;
    });
  }, [filtered, sort]);

  const changed = filtered.filter((row) => row.delta !== 0).length;
  const compareSet = new Set(compare);

  function choose(key: SortKey) {
    setSort((current) =>
      current.key === key
        ? { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: key === 'country' ? 'asc' : 'asc' },
    );
  }

  function ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
    if (sort.key !== key) return 'none';
    return sort.dir === 'asc' ? 'ascending' : 'descending';
  }

  return (
    <div className="robustness">
      <p className="pane__callout">
        {changed} of {filtered.length} countries change rank between the two
        normalizations. Most barely move; sorted smallest difference first.
      </p>

      <div className="robustness__wrap" tabIndex={0} role="region" aria-label="Normalization robustness table, scrollable">
        <table className="data-table robustness__table">
          <caption className="sr-only">
            Rank under min–max and z-score, with the difference, for every country in the
            selected group.
          </caption>
          <thead>
            <tr>
              <th scope="col" aria-sort={ariaSort('country')}>
                <button type="button" onClick={() => choose('country')}>
                  Country <span aria-hidden="true">↕</span>
                </button>
              </th>
              <th scope="col" className="col-minmax" aria-sort={ariaSort('rankFull')}>
                <button type="button" onClick={() => choose('rankFull')}>
                  Min–max rank <span aria-hidden="true">↕</span>
                </button>
              </th>
              <th scope="col" className="col-z" aria-sort={ariaSort('rankZ')}>
                <button type="button" onClick={() => choose('rankZ')}>
                  Z-score rank <span aria-hidden="true">↕</span>
                </button>
              </th>
              <th scope="col" aria-sort={ariaSort('delta')}>
                <button type="button" onClick={() => choose('delta')}>
                  Difference <span aria-hidden="true">↕</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr
                key={row.iso3}
                className={compareSet.has(row.iso3) ? 'is-compared' : undefined}
                data-robustness={row.iso3}
              >
                <th scope="row">{row.shortName || row.country}</th>
                <td className="col-minmax">{row.rankFull}</td>
                <td className="col-z">{row.rankZ}</td>
                <td>
                  <span
                    className={`delta-pill ${
                      row.delta === 0
                        ? 'delta-pill--none'
                        : row.delta > 0
                          ? 'delta-pill--down'
                          : 'delta-pill--up'
                    }`}
                  >
                    {row.delta === 0 ? '0' : row.delta > 0 ? `−${row.delta}` : `+${Math.abs(row.delta)}`}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="micro hint">
        Individual indicator ranks are unchanged by construction: z-score is a monotone
        transform of min–max, so only the composite moves. A negative difference means
        the z-score ranks the country higher.
      </p>
    </div>
  );
}
