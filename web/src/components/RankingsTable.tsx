import { PARTIAL_DATA_COVERAGE, pillarCode } from '../lib/constants';
import { formatComposite, formatPercent, formatRank, formatScore } from '../lib/format';
import { methodLabel, withScale } from '../lib/scale';
import type { PillarLite, ScoreRow, SortKey, SortState } from '../lib/types';
import MissingValue from './MissingValue';
import ScoreBar from './ScoreBar';

interface RankingsTableProps {
  rows: ScoreRow[];
  allCount: number;
  edition: string;
  pillars: PillarLite[];
  median: number;
  mode: 'rank' | 'score';
  showPillars: boolean;
  sort: SortState;
  onSort: (key: SortKey) => void;
  scale: string;
  defaultScale: string;
  /** Present only when the active scale is not min–max. */
  baselineRanks: Record<string, number> | null;
}

function sortDirectionWord(key: SortKey, dir: 'asc' | 'desc'): string {
  if (key === 'country') return dir === 'asc' ? 'A to Z' : 'Z to A';
  if (key === 'rank') return dir === 'asc' ? 'best rank first' : 'lowest rank first';
  return dir === 'desc' ? 'highest first' : 'lowest first';
}

function sortLabel(key: SortKey): string {
  if (key === 'rank') return 'rank';
  if (key === 'country') return 'country';
  return 'score';
}

export default function RankingsTable({
  rows,
  allCount,
  edition,
  pillars,
  median,
  mode,
  showPillars,
  sort,
  onSort,
  scale,
  defaultScale,
  baselineRanks,
}: RankingsTableProps) {
  const visible = rows.length;

  function ariaSort(key: SortKey): 'ascending' | 'descending' | 'none' {
    if (sort.key !== key) return 'none';
    return sort.dir === 'asc' ? 'ascending' : 'descending';
  }

  function glyph(key: SortKey): string {
    if (sort.key !== key) return '↕';
    return sort.dir === 'asc' ? '▲' : '▼';
  }

  function pillarCell(row: ScoreRow, pillar: PillarLite) {
    const value = row.pillars[pillar.id];
    if (!value || value.score === null) {
      const missing = Object.entries(row.subPillars).filter(
        ([key, item]) => key.startsWith(`${pillar.id} · `) && item.status !== 'present',
      );
      const names = missing.map(([key]) => key.split(' · ')[1]).join(', ');
      const detail = missing.length
        ? `${pillar.id} is not scored for ${row.shortName || row.country} — ${names} ${missing.length === 1 ? 'is' : 'are'} not scored because too many indicators are missing.`
        : `${pillar.id} is not scored for ${row.shortName || row.country}.`;
      return <MissingValue detail={detail} />;
    }
    return (
      <span title={`${pillar.id}, rank ${formatRank(value.rank)} of ${allCount}`}>
        {formatScore(value.score)}
      </span>
    );
  }

  function movementCell(row: ScoreRow) {
    const before = baselineRanks?.[row.iso3];
    if (before === undefined) return <span className="cell-quiet">—</span>;
    const delta = before - row.rank;
    if (delta === 0) {
      return (
        <>
          <span aria-hidden="true">—</span>
          <span className="sr-only">no change compared with min–max</span>
        </>
      );
    }
    const up = delta > 0;
    const amount = Math.abs(delta);
    return (
      <span className={up ? 'rank-up' : 'rank-down'}>
        <span aria-hidden="true">
          {up ? '▲' : '▼'} {up ? '+' : '−'}
          {amount}
        </span>
        <span className="sr-only">
          {up ? 'up' : 'down'} {amount} {amount === 1 ? 'place' : 'places'} compared with
          min–max
        </span>
      </span>
    );
  }

  return (
    <div className="panel rankings-table">
      <table>
        <caption className="sr-only">
          CHIPS rankings, {edition} edition. {visible} of {allCount} countries
          shown, sorted by {sortLabel(sort.key)}, {sortDirectionWord(sort.key, sort.dir)}.
          {baselineRanks
            ? ' Rank movement is shown against the min–max scale.'
            : ''}
        </caption>
        <thead>
          <tr>
            <th scope="col" className="num rank-col" aria-sort={ariaSort('rank')}>
              <button type="button" className="sort-button" onClick={() => onSort('rank')}>
                <span aria-hidden="true">#</span>
                <span className="sr-only">Rank</span>
                <span className="sort-button__glyph" aria-hidden="true">
                  {glyph('rank')}
                </span>
              </button>
            </th>
            <th scope="col" aria-sort={ariaSort('country')}>
              <button type="button" className="sort-button" onClick={() => onSort('country')}>
                <span>Country</span>
                <span className="sort-button__glyph" aria-hidden="true">
                  {glyph('country')}
                </span>
              </button>
            </th>
            <th scope="col" className="num score-col" aria-sort={ariaSort('score')}>
              <button type="button" className="sort-button" onClick={() => onSort('score')}>
                <span>CHIPS score (0–100)</span>
                <span className="sort-button__glyph" aria-hidden="true">
                  {glyph('score')}
                </span>
              </button>
            </th>
            {baselineRanks && (
              <th scope="col" className="num movement-col">
                <abbr title="Rank movement compared with the min–max scale">
                  Rank vs min–max
                </abbr>
              </th>
            )}
            {showPillars &&
              pillars.map((pillar) => (
                <th scope="col" className="num pillar-col" key={pillar.id}>
                  <abbr title={pillar.id} style={{ textDecoration: 'none' }}>
                    {pillarCode(pillar.id)}
                  </abbr>
                  <span className="sr-only"> {pillar.id}</span>
                </th>
              ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const name = row.shortName || row.country;
            const partial = row.coverage < PARTIAL_DATA_COVERAGE;
            return (
              <tr key={row.iso3}>
                <td className={`num rank-cell${mode === 'rank' ? ' emphasis' : ''}`}>
                  {formatRank(row.rank)}
                </td>
                <td>
                  <div className="country-cell">
                    <a
                      className="country-link"
                      href={withScale(`/country/${row.iso3}`, scale, defaultScale)}
                    >
                      {name}
                    </a>
                    {partial && (
                      <span
                        className="chip chip--partial"
                        title={`Coverage ${formatPercent(row.coverage)} — ${row.indicatorsPresent} of ${row.indicatorsTotal} indicators`}
                      >
                        Partial data
                        <span className="sr-only">
                          {' '}
                          — coverage {formatPercent(row.coverage)}, {row.indicatorsPresent} of{' '}
                          {row.indicatorsTotal} indicators
                        </span>
                      </span>
                    )}
                  </div>
                </td>
                <td className="num">
                  <div className="score-cell">
                    <span className={`score-cell__value${mode === 'score' ? ' emphasis' : ''}`}>
                      {formatComposite(row.overall)}
                    </span>
                    <ScoreBar
                      score={row.overall}
                      median={median}
                      encode={mode === 'rank' ? 'rank' : 'score'}
                      rank={row.rank}
                      total={allCount}
                    />
                  </div>
                </td>
                {baselineRanks && (
                  <td className="num movement-col">{movementCell(row)}</td>
                )}
                {showPillars &&
                  pillars.map((pillar) => (
                    <td className="num pillar-col pillar-value" key={pillar.id}>
                      {pillarCell(row, pillar)}
                    </td>
                  ))}
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="table-note">
        <span>
          {visible} of {allCount} countries
        </span>
        <span>Scores 0–100</span>
        <span>{edition} Absolute edition</span>
        <span>{methodLabel(scale)} scaling</span>
        {baselineRanks && <span>Movement: rank vs min–max</span>}
        <span>Bar tick: median {formatScore(median)}</span>
        <span>Rank and score share one order; the emphasis control changes which number is large.</span>
        {showPillars && (
          <span className="pillar-legend">
            {pillars.map((pillar) => (
              <span key={pillar.id}>
                <span className="pillar-code" data-pillar={pillar.id}>
                  {pillarCode(pillar.id)}
                </span>{' '}
                {pillar.id}
              </span>
            ))}
          </span>
        )}
        <span className="chip chip--placeholder">Download CSV — later wave</span>
      </div>
    </div>
  );
}
