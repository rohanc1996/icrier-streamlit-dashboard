import { formatPercent, formatRank, formatScore } from '../lib/format';
import { pillarCode } from '../lib/constants';
import type { Pillar } from '../lib/types';
import MissingValue from './MissingValue';

interface PillarCardProps {
  pillar: Pillar;
  score: number | null;
  rank: number | null;
  countryCount: number;
  notScored: number;
  open: boolean;
  panelId: string;
  onToggle: (scrollIntoView: boolean) => void;
}

/**
 * One pillar summary card (IA §8). The header button owns the disclosure:
 * `aria-expanded` / `aria-controls` point at the PillarDetail panel below the
 * card row. This card stays read-only apart from that button.
 */
export default function PillarCard({
  pillar,
  score,
  rank,
  countryCount,
  notScored,
  open,
  panelId,
  onToggle,
}: PillarCardProps) {
  const subCount = pillar.subPillars.length;
  const indicatorTotal = pillar.subPillars.reduce(
    (total, sub) => total + sub.leaves.length,
    0,
  );
  const detail = subCount === 1 ? `${indicatorTotal} indicators` : `${subCount} sub-pillars`;
  const headingId = `pillar-${pillar.id}`;

  return (
    <article
      className="pillar-card"
      data-pillar={pillar.id}
      data-open={open}
      aria-labelledby={headingId}
    >
      <div className="pillar-card__head">
        <h3 className="pillar-card__name" id={headingId}>
          <button
            type="button"
            className="pillar-card__toggle"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={(event) => {
              event.currentTarget.focus();
              onToggle(event.detail > 0);
            }}
          >
            <span>{pillar.id}</span>
            <span className="pillar-code" aria-hidden="true">
              {pillarCode(pillar.id)}
            </span>
            <span className="pillar-card__action" aria-hidden="true">
              <span className="pillar-card__action-label">{open ? 'Hide' : 'Show'}</span>
              <span className="chevron">{open ? '▴' : '▾'}</span>
            </span>
            <span className="sr-only"> {open ? 'Hide' : 'Show'} details</span>
          </button>
        </h3>
      </div>

      <p className="pillar-card__score">
        {score === null ? (
          <MissingValue detail={`${pillar.id} is not scored for this country.`} variant="inline" />
        ) : (
          formatScore(score)
        )}
      </p>

      <dl className="pillar-card__meta">
        <div>
          <dt>Rank</dt>
          <dd>
            {formatRank(rank)} of {countryCount}
          </dd>
        </div>
        <div>
          <dt>Weight</dt>
          <dd>{formatPercent(pillar.weight, 1)}</dd>
        </div>
        <div>
          <dt>Detail</dt>
          <dd>{detail}</dd>
        </div>
      </dl>

      {notScored > 0 && (
        <p className="pillar-card__missing">
          <span className="chip chip--partial">
            {notScored} of {subCount} not scored
          </span>
        </p>
      )}
    </article>
  );
}
