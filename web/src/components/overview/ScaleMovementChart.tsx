import type { ScaleMovementChartModel } from '../../lib/overview-types';

/**
 * Pane 6: the same 71 scores under two scaling methods, drawn as diverging
 * bars. `delta = rankZ − rankFull`, so a bar to the left means the z-score
 * ranks that country higher. Direction is carried by the side of the zero line
 * and by the two printed ranks, not by a second colour.
 *
 * The headline above the chart is the pane's main claim, not a subtitle: it is
 * the count of countries whose rank changes, read from the payload.
 */
export default function ScaleMovementChart({
  model,
}: {
  model: ScaleMovementChartModel;
}) {
  return (
    <div
      className="diverging-chart"
      role="group"
      aria-label={model.ariaLabel}
    >
      <p className="pane__callout">{model.headline}</p>

      <p className="diverging__key">
        <span aria-hidden="true">←</span> {model.gainLabel}
        <span className="diverging__key-sep" aria-hidden="true">
          ·
        </span>
        {model.lossLabel} <span aria-hidden="true">→</span>
      </p>

      <ol className="diverging">
        <li className="diverging__head" aria-hidden="true">
          <span>Country</span>
          <span>rank change from min–max</span>
          <span>min–max → z · Δ</span>
        </li>

        {model.rows.map((row) => (
          <li
            className="diverging__row"
            key={row.iso3}
            data-diverge={row.iso3}
            data-delta={row.delta}
          >
            <span className="diverging__name" title={row.label}>
              {row.label}
            </span>
            <svg
              className="diverging__track"
              width="100%"
              height="22"
              aria-hidden="true"
              focusable="false"
            >
              <line className="diverging__zero" x1="50%" y1="0" x2="50%" y2="22" />
              <rect
                className={
                  row.side === 'better'
                    ? 'diverging__bar diverging__bar--better'
                    : 'diverging__bar diverging__bar--worse'
                }
                x={`${row.startPct}%`}
                y="5"
                width={`${row.widthPct}%`}
                height="12"
                rx="1"
              />
            </svg>
            <span className="diverging__value" data-rank-text={row.rankText}>
              {row.rankText}
              <span className="diverging__delta"> · {row.deltaText}</span>
              <span className="sr-only"> under z</span>
            </span>
          </li>
        ))}

        <li className="diverging__axis" aria-hidden="true">
          <span />
          <svg className="diverging__axis-track" width="100%" height="24">
            {model.ticks.map((tick, index) => (
              <g
                key={tick.pct}
                className={index % 2 === 1 ? 'diverging__tick--minor' : undefined}
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
                  y="16"
                  textAnchor={tick.pct === 0 ? 'start' : tick.pct === 100 ? 'end' : 'middle'}
                >
                  {tick.label}
                </text>
              </g>
            ))}
          </svg>
          <span className="diverging__axis-label">places</span>
        </li>
      </ol>
    </div>
  );
}
