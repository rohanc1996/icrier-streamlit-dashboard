import { Fragment } from 'react';
import { formatPercent, formatScore } from '../lib/format';
import { slugify } from '../lib/open';
import type { IndicatorRow, Pillar, ScoreRow, SubPillar } from '../lib/types';
import IndicatorTable from './IndicatorTable';
import MissingValue from './MissingValue';

interface SubPillarTableProps {
  pillar: Pillar;
  countryName: string;
  subPillars: ScoreRow['subPillars'];
  subPillarOf: Record<string, number>;
  indicatorRows: IndicatorRow[];
  openSub: string | null;
  onToggleSub: (sub: SubPillar) => void;
  baseId: string;
}

/**
 * L2: the sub-pillars inside one pillar. Rows stay in place when a sub-pillar
 * is not scored; the score becomes the words "Not scored", the weight becomes
 * "0% (redistributed)", and the reason sits on the next line.
 */
export default function SubPillarTable({
  pillar,
  countryName,
  subPillars,
  subPillarOf,
  indicatorRows,
  openSub,
  onToggleSub,
  baseId,
}: SubPillarTableProps) {
  return (
    <table className="subpillar-table">
      <caption className="sr-only">
        {pillar.id} sub-pillars for {countryName}
      </caption>
      <thead>
        <tr>
          <th scope="col">Sub-pillar</th>
          <th scope="col" className="num">
            Score (0–100)
          </th>
          <th scope="col" className="num">
            World rank
          </th>
          <th scope="col" className="num weight-col">
            Weight in pillar
          </th>
        </tr>
      </thead>
      <tbody>
        {pillar.subPillars.map((sub) => {
          const state = subPillars[sub.key];
          const missing = !state || state.status !== 'present' || state.score === null;
          const rank = state?.rank ?? null;
          const of = subPillarOf[sub.key] ?? 0;
          const isOpen = openSub === sub.key;
          const panelId = `${baseId}-sub-${slugify(sub.key)}`;
          const reason = state?.reason ?? 'no data reported';

          return (
            <Fragment key={sub.key}>
              <tr data-subpillar={sub.key} data-open={isOpen}>
                <th scope="row">
                  <button
                    type="button"
                    className="subpillar-toggle"
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={(event) => {
                      // Keep focus on the control when the panel below it
                      // disappears (WebKit does not focus a clicked button).
                      event.currentTarget.focus();
                      onToggleSub(sub);
                    }}
                  >
                    <span className="subpillar-toggle__name">{sub.name}</span>
                    <span className="row-sub">
                      {missing
                        ? 'Weight 0% (redistributed)'
                        : `Weight ${formatPercent(sub.weight, 1)}`}
                    </span>
                    <span className="subpillar-toggle__action">
                      <span aria-hidden="true">{isOpen ? 'Hide' : 'Show'}</span>
                      <span className="chevron" aria-hidden="true">
                        {isOpen ? '▴' : '▾'}
                      </span>
                      <span className="sr-only">
                        {' '}
                        {isOpen ? 'Hide' : 'Show'} indicators for {sub.name}
                      </span>
                    </span>
                  </button>
                  {missing && <span className="missing-reason">{reason}</span>}
                </th>
                <td className="num">
                  {missing ? (
                    <MissingValue variant="inline" detail={reason} />
                  ) : (
                    formatScore(state.score)
                  )}
                </td>
                <td className="num">
                  {missing ? (
                    <MissingValue detail="The sub-pillar is not scored, so it has no rank." />
                  ) : rank !== null ? (
                    `${rank} of ${of}`
                  ) : (
                    <>
                      <span aria-hidden="true">—</span>
                      <span className="sr-only">not ranked</span>
                    </>
                  )}
                </td>
                <td className="num weight-col">
                  {missing ? (
                    <span
                      title={`Framework weight ${formatPercent(sub.weight, 1)}; redistributed because the sub-pillar is not scored`}
                    >
                      0% (redistributed)
                    </span>
                  ) : (
                    formatPercent(sub.weight, 1)
                  )}
                </td>
              </tr>
              <tr className="subpillar-panel" hidden={!isOpen}>
                <td colSpan={4}>
                  <div id={panelId}>
                    {isOpen && (
                      <>
                        {missing && (
                          <p className="micro hint subpillar-panel__note">
                            This sub-pillar is not scored; the rows below are its
                            underlying indicators and do not affect the pillar.
                          </p>
                        )}
                        <IndicatorTable
                          sub={sub}
                          rows={indicatorRows}
                          countryName={countryName}
                        />
                      </>
                    )}
                  </div>
                </td>
              </tr>
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
