import { clamp, to100 } from '../lib/format';

interface ScoreBarProps {
  /** Raw 0–1 score from the export. */
  score: number;
  /** Raw 0–1 edition median, drawn as a 1px tick. */
  median: number;
  /** Encode score length, or position from the top of the table. */
  encode?: 'score' | 'rank';
  rank?: number | null;
  total?: number;
}

/**
 * 0–100 fill with a median tick. Drawn filled, never animated from zero.
 * The value is always printed next to it, so the bar is never the only route
 * to the number.
 */
export default function ScoreBar({
  score,
  median,
  encode = 'score',
  rank = null,
  total = 0,
}: ScoreBarProps) {
  const scorePercent = clamp(to100(score));
  const rankPercent =
    encode === 'rank' && rank !== null && total > 0
      ? clamp(((total - rank + 1) / total) * 100)
      : null;
  const fill = rankPercent ?? scorePercent;
  const tick = clamp(to100(median));

  return (
    <div className="scorebar" aria-hidden="true">
      <div className="scorebar__track">
        <div className="scorebar__fill" style={{ width: `${fill}%` }} />
        <div className="scorebar__tick" style={{ left: `${tick}%` }} />
      </div>
    </div>
  );
}
