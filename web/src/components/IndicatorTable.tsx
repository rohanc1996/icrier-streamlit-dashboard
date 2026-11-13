import { formatPercent, formatRank, formatScore } from '../lib/format';
import type { IndicatorRow, SubPillar } from '../lib/types';
import MissingValue from './MissingValue';

interface IndicatorTableProps {
  sub: SubPillar;
  rows: IndicatorRow[];
  countryName: string;
}

/**
 * L3: the indicators inside one sub-pillar. A real table with a caption and
 * scoped headers; missing values use words, never 0 and never a blank.
 *
 * Weights: the export's `effectiveWeight` is the leaf's *global* weight
 * (0.015625 = 0.25 pillar × 0.25 sub-pillar × 0.25 leaf), so it is not a
 * sub-pillar share. The local share comes from the framework:
 * `weightInGroup × groupWeight` (groupWeight is 1 for flat sub-pillars).
 */
export default function IndicatorTable({ sub, rows, countryName }: IndicatorTableProps) {
  const byLeaf = new Map(rows.map((row) => [row.leaf, row]));

  return (
    <div className="indicator-wrap">
      <table className="indicator-table">
        <caption className="sr-only">
          {sub.name} indicators for {countryName}
        </caption>
        <thead>
          <tr>
            <th scope="col">Indicator</th>
            <th scope="col" className="num">
              Score (0–100)
            </th>
            <th scope="col" className="num">
              World rank
            </th>
            <th scope="col" className="num weight-col">
              Weight in sub-pillar
            </th>
          </tr>
        </thead>
        <tbody>
          {sub.leaves.map((leaf) => {
            const row = byLeaf.get(leaf.name);
            const missing = !row || row.status !== 'present' || row.score === null;
            const localWeight = leaf.weightInGroup * (leaf.groupWeight ?? 1);
            const rank =
              !missing && row?.rank !== null && row?.rank !== undefined
                ? `${formatRank(row.rank)} of ${row.of}`
                : null;
            const reason = row?.reason ?? 'no data reported';

            return (
              <tr key={leaf.name} data-indicator={leaf.name}>
                <th scope="row" className="indicator-name">
                  <span>{leaf.label || leaf.name}</span>
                  <span className="row-sub">Weight {formatPercent(localWeight, 1)}</span>
                </th>
                <td className="num">
                  {missing ? (
                    <MissingValue variant="inline" detail={reason} showDetail />
                  ) : (
                    formatScore(row.score)
                  )}
                </td>
                <td className="num">
                  {missing ? (
                    <MissingValue detail="The indicator is not scored, so it has no rank." />
                  ) : rank ? (
                    rank
                  ) : (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">not ranked</span>
                    </>
                  )}
                </td>
                <td className="num weight-col">{formatPercent(localWeight, 1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="table-caption micro hint">
        Weights are the framework's local weights inside this sub-pillar. When values are
        missing they are redistributed at scoring time.
      </p>
    </div>
  );
}
