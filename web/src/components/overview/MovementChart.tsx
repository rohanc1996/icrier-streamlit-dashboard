import type { MovementChartModel } from '../../lib/overview-types';

/**
 * Pane 5: one dumbbell per country, both ends on a fixed 0–100 score axis.
 *
 * Rank is not encoded anywhere — a rank is a position in a 71-country
 * ordering, and that ordering changed composition between editions, so it is
 * a misleading slope. The score is the quantity; the rank comparison lives in
 * the table and in the pane's "what this shows" line.
 *
 * The rows are real text, so a reader gets the name and the change without the
 * SVG. The pale-to-ink convention says which end is the later edition and holds
 * for any number of editions.
 */
export default function MovementChart({ model }: { model: MovementChartModel }) {
  const firstYear = model.years[0];
  const lastYear = model.years[model.years.length - 1];

  return (
    <div className="movement-chart" role="group" aria-label={model.ariaLabel}>
      <p className="movement-chart__caveat">{model.caveat}</p>

      <p className="movement-chart__key">
        <span className="movement-chart__swatch movement-chart__swatch--first" aria-hidden="true" />
        {firstYear}
        <span className="movement-chart__arrow" aria-hidden="true">
          →
        </span>
        <span className="movement-chart__swatch movement-chart__swatch--last" aria-hidden="true" />
        {lastYear}
        <span className="movement-chart__key-note">
          pale to ink · the five largest score changes on this scale are marked
        </span>
      </p>

      <ol className="movement">
        <li className="movement__head" aria-hidden="true">
          <span>Country</span>
          <span>CHIPS score, 0–100</span>
          <span>Δ points</span>
        </li>

        {model.rows.map((row) => {
          const lastPoint = row.points[row.points.length - 1];
          return (
            <li
              className={`movement__row${
                row.highlighted ? ' movement__row--marked' : ''
              }`}
              key={row.iso3}
              data-dumbbell={row.iso3}
              data-highlighted={row.highlighted ? 'true' : undefined}
              data-delta={row.deltaPoints ?? undefined}
            >
              <span className="movement__name" title={row.label}>
                {row.label}
              </span>
              <svg
                className="movement__track"
                width="100%"
                height="20"
                aria-hidden="true"
                focusable="false"
              >
                {model.ticks.map((tick) => (
                  <line
                    key={tick.label}
                    className="movement__grid"
                    x1={`${tick.pct}%`}
                    y1="0"
                    x2={`${tick.pct}%`}
                    y2="20"
                  />
                ))}
                {row.segments.map((segment, index) => (
                  <line
                    key={`${segment.from.year}-${index}`}
                    className="movement__connector"
                    x1={`${segment.from.xPct}%`}
                    y1="10"
                    x2={`${segment.to.xPct}%`}
                    y2="10"
                  />
                ))}
                {row.points.map((point) => (
                  <circle
                    key={point.year}
                    data-dumbbell-point={point.year}
                    className={
                      point === lastPoint
                        ? 'movement__dot movement__dot--last'
                        : 'movement__dot'
                    }
                    cx={`${point.xPct}%`}
                    cy="10"
                    r={point === lastPoint ? 4.2 : 3.4}
                  />
                ))}
              </svg>
              <span className="movement__delta">{row.deltaText}</span>
              <span className="sr-only">
                {row.points.length > 1
                  ? `${row.label}: ${row.points
                      .map((point) => `${point.year} ${Number((point.score * 100).toFixed(2))}`)
                      .join(', ')}; change ${row.deltaText} points.`
                  : `${row.label}: scored in ${row.points.length} edition.`}
              </span>
            </li>
          );
        })}

        <li className="movement__axis" aria-hidden="true">
          <span />
          <svg className="movement__axis-track" width="100%" height="26">
            <line
              className="chart__axis"
              x1={`${model.ticks[0]?.pct ?? 0}%`}
              y1="0"
              x2={`${model.ticks[model.ticks.length - 1]?.pct ?? 100}%`}
              y2="0"
            />
            {model.ticks.map((tick, index) => (
              <g
                key={tick.label}
                className={
                  index === 0 || index === model.ticks.length - 1
                    ? undefined
                    : 'movement__tick--minor'
                }
              >
                <line
                  className="chart__tick"
                  x1={`${tick.pct}%`}
                  y1="0"
                  x2={`${tick.pct}%`}
                  y2="4"
                />
                <text
                  className="chart__tick-label"
                  x={`${tick.pct}%`}
                  y="17"
                  textAnchor={
                    index === 0 ? 'start' : index === model.ticks.length - 1 ? 'end' : 'middle'
                  }
                >
                  {tick.label}
                </text>
              </g>
            ))}
          </svg>
          <span />
        </li>
      </ol>
    </div>
  );
}
