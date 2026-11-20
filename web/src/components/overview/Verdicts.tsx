import type { VerdictMark } from '../lib/site';

interface VerdictsProps {
  country: string;
  marks: VerdictMark[];
  best: { id: string; rank: number } | null;
  worst: { id: string; rank: number } | null;
}

/**
 * Pane 4: the selected country's rank in each pillar, against every country's
 * rank in that pillar. The dots are the field; the marker is the country.
 * Ranks are positions inside a pillar, never the overall rank.
 */
export default function Verdicts({ country, marks, best, worst }: VerdictsProps) {
  return (
    <div className="verdicts">
      <p className="verdicts__headline">
        {country} ranks{' '}
        {best ? (
          <strong>
            {best.rank}
            {suffix(best.rank)} in {best.id}
          </strong>
        ) : (
          '—'
        )}
        {worst ? (
          <>
            {' '}and{' '}
            <strong>
              {worst.rank}
              {suffix(worst.rank)} in {worst.id}
            </strong>
          </>
        ) : null}
        .
      </p>

      <ol className="verdicts__rows">
        {marks.map((mark) => (
          <li className="verdicts__row" key={mark.id} data-verdict={mark.id}>
            <span className="verdicts__name">{mark.id}</span>
            <svg
              className="verdicts__track"
              width="100%"
              height="30"
              role="img"
              aria-label={`${country} is rank ${mark.rank} of ${mark.of} in ${mark.id}`}
            >
              {mark.points.map((point, index) => (
                <circle
                  key={`${point.rank}-${index}`}
                  className="verdicts__dot"
                  cx={`${point.xPct}%`}
                  cy={15 + point.dy}
                  r="2"
                />
              ))}
              <line
                className="verdicts__marker"
                x1={`${mark.xPct}%`}
                y1="2"
                x2={`${mark.xPct}%`}
                y2="28"
              />
              <circle
                className="verdicts__marker-dot"
                cx={`${mark.xPct}%`}
                cy="15"
                r="4.5"
              />
            </svg>
            <span className="verdicts__value">
              <strong>{mark.rank}</strong>
              <span className="verdicts__of"> of {mark.of}</span>
            </span>
            <span className="verdicts__score">{mark.scoreText}</span>
          </li>
        ))}
      </ol>
      <p className="micro hint">
        Each dot is one country&apos;s rank within that pillar; 1 is best. A pillar rank
        is not the overall rank.
      </p>
    </div>
  );
}

function suffix(value: number): string {
  const rest = value % 100;
  if (rest >= 11 && rest <= 13) return 'th';
  return value % 10 === 1 ? 'st' : value % 10 === 2 ? 'nd' : value % 10 === 3 ? 'rd' : 'th';
}
