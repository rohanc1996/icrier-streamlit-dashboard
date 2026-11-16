import type { CompositionChartModel } from '../../lib/overview-types';

/**
 * Pane 3: one stacked bar per country. Each segment's width is the exporter's
 * `contribution` (pillar score × nominal weight) on a shared axis, so the bar
 * lengths are comparable across rows and the segments are a decomposition of
 * the score rather than a decoration of it.
 *
 * The SVG carries the marks; the row's rank, name and total are real text, and
 * the "View as table" beside the chart carries country/pillar/contribution/
 * score for every segment.
 */
export default function CompositionChart({ model }: { model: CompositionChartModel }) {
  const maxTick = model.ticks[model.ticks.length - 1]?.label ?? '';

  return (
    <div className="composition-chart">
      <ul className="composition__legend" aria-label="Pillar legend">
        {model.legend.map((item) => (
          <li className="composition__legend-item" key={item.id} data-legend={item.id}>
            <span
              className={`composition__swatch composition__swatch--${item.id.toLowerCase()}`}
              aria-hidden="true"
            />
            <span className="composition__legend-label">{item.label}</span>
            {item.weightText && (
              <span className="composition__weight">{item.weightText}</span>
            )}
          </li>
        ))}
      </ul>

      <ol className="composition">
        {model.rows.map((row) => (
          <li
            className="composition__row"
            key={row.iso3}
            data-composition-country={row.iso3}
            data-total={row.total}
          >
            <span className="composition__rank">{row.rank}</span>
            <span className="composition__name" title={row.label}>
              {row.label}
            </span>
            <svg
              className="composition__track"
              width="100%"
              height="20"
              aria-hidden="true"
              focusable="false"
            >
              {row.segments.map((segment) => (
                <rect
                  key={segment.id}
                  className={`composition__segment composition__segment--${segment.id.toLowerCase()}`}
                  data-segment={segment.id}
                  data-contribution={segment.contribution}
                  x={`${segment.startPct}%`}
                  y="2"
                  width={`${segment.widthPct}%`}
                  height="16"
                  rx="1"
                >
                  <title>{`${segment.id}: ${segment.text}`}</title>
                </rect>
              ))}
            </svg>
            <span className="composition__value">{row.totalText}</span>
          </li>
        ))}

        <li className="composition__axis" aria-hidden="true">
          <span />
          <span />
          <svg className="composition__axis-track" width="100%" height="18">
            {model.ticks.map((tick, index) => (
              <g
                key={tick.label}
                className={index % 2 === 1 ? 'composition__tick--minor' : undefined}
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
                  y="15"
                  textAnchor="middle"
                >
                  {tick.label}
                </text>
              </g>
            ))}
          </svg>
          <span />
        </li>
      </ol>

      <p className="composition__note">
        Score axis 0–{maxTick}. Segments are the weighted pillar contributions; their
        sum is the CHIPS score printed at the end of each bar.
      </p>
    </div>
  );
}
