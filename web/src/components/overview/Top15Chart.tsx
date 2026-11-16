import type { Top15ChartModel } from '../../lib/overview-types';

/**
 * Lollipop of the top 15. One row per country; the top three carry ink and the
 * rest stay muted, so the gap between the podium and the pack is visible
 * without a second colour or a cut-off.
 *
 * The rows are real text, so assistive technology reads the same numbers the
 * marks encode. The line and dot are decorative and hidden from it.
 */
export default function Top15Chart({ model }: { model: Top15ChartModel }) {
  return (
    <div className="lollipop-chart">
      <p className="pane__callout">
        Places 4–13 span <strong>{model.spanFrom}</strong> →{' '}
        <strong>{model.spanTo}</strong>
      </p>
      <ol className="lollipop">
        {model.rows.map((row) => (
          <li
            className={`lollipop__row${row.isTop3 ? ' lollipop__row--top' : ''}`}
            key={row.iso3}
            data-lollipop={row.iso3}
          >
            <span className="lollipop__rank">{row.rank}</span>
            <span className="lollipop__name">{row.label}</span>
            <svg
              className="lollipop__track"
              width="100%"
              height="18"
              aria-hidden="true"
              focusable="false"
            >
              <line
                className="lollipop__line"
                x1="0"
                y1="9"
                x2={`${row.pct}%`}
                y2="9"
              />
              <circle className="lollipop__dot" cx={`${row.pct}%`} cy="9" r="5" />
            </svg>
            <span className="lollipop__value">{row.scoreText}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
