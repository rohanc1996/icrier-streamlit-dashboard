import { formatPercent, formatScore, formatRank } from '../lib/format';
import type { IndicatorRow, Pillar, ScoreRow, SubPillar } from '../lib/types';
import IndicatorTable from './IndicatorTable';
import SubPillarTable from './SubPillarTable';

interface PillarDetailProps {
  pillar: Pillar;
  open: boolean;
  panelId: string;
  countryName: string;
  score: number | null;
  rank: number | null;
  countryCount: number;
  notScored: number;
  subPillars: ScoreRow['subPillars'];
  subPillarOf: Record<string, number>;
  indicatorRows: IndicatorRow[];
  openSub: string | null;
  onToggleSub: (sub: SubPillar) => void;
  baseId: string;
}

/**
 * L1/L2 detail panel. One panel per pillar exists in the DOM so every card's
 * `aria-controls` resolves; content is rendered only while open. Closing the
 * panel never removes the header button, so focus stays where the user put it.
 */
export default function PillarDetail({
  pillar,
  open,
  panelId,
  countryName,
  score,
  rank,
  countryCount,
  notScored,
  subPillars,
  subPillarOf,
  indicatorRows,
  openSub,
  onToggleSub,
  baseId,
}: PillarDetailProps) {
  const headingId = `${panelId}-heading`;
  const singleSubPillar = pillar.subPillars.length === 1;
  const indicatorTotal = pillar.subPillars.reduce(
    (total, sub) => total + sub.leaves.length,
    0,
  );

  return (
    <section
      id={panelId}
      className="pillar-detail"
      data-pillar={pillar.id}
      aria-labelledby={headingId}
      hidden={!open}
    >
      <header className="pillar-detail__head">
        <div>
          <h3 className="display-m" id={headingId}>
            {pillar.id}
          </h3>
          <p className="body-s hint pillar-detail__line">
            {score === null ? 'Not scored' : `Score ${formatScore(score)} of 100`} · rank{' '}
            {formatRank(rank)} of {countryCount} · weight{' '}
            {formatPercent(pillar.weight, 1)} ·{' '}
            {notScored === 0
              ? `all ${pillar.subPillars.length} sub-pillars scored`
              : `${notScored} of ${pillar.subPillars.length} sub-pillars not scored`}
          </p>
        </div>
      </header>

      {open &&
        (singleSubPillar ? (
          <>
            <p className="micro hint subpillar-panel__note">
              This pillar's only sub-pillar repeats the pillar name, so the panel opens
              straight onto its {indicatorTotal} indicators.
            </p>
            <IndicatorTable
              sub={pillar.subPillars[0]}
              rows={indicatorRows}
              countryName={countryName}
            />
          </>
        ) : (
          <SubPillarTable
            pillar={pillar}
            countryName={countryName}
            subPillars={subPillars}
            subPillarOf={subPillarOf}
            indicatorRows={indicatorRows}
            openSub={openSub}
            onToggleSub={onToggleSub}
            baseId={baseId}
          />
        ))}
    </section>
  );
}
