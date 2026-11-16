import type { IndiaChartModel } from '../../lib/overview-types';

/**
 * Pane 4: five rows, one per pillar. The pale strip is every country's rank in
 * that pillar on a shared 1–71 axis; the accent-ink marker is India. The two
 * headline facts sit above the plot so the 2-versus-66 contrast is read before
 * the eye has to compare positions.
 *
 * Positions are percentages horizontally, so the plot narrows rather than
 * scrolls; the marks stay decorative and each row prints India's rank.
 */
export default function IndiaChart({ model }: { model: IndiaChartModel }) {
  return (
    <div className="verdict-chart">
      <div className="verdict__facts">
        <div className="verdict__fact">
          <p className="verdict__fact-value">{model.best.rank}</p>
          <p className="verdict__fact-label">
            {model.best.id} · of {model.of}
          </p>
        </div>
        <p className="verdict__fact-versus" aria-hidden="true">
          against
        </p>
        <div className="verdict__fact verdict__fact--weak">
          <p className="verdict__fact-value">{model.worst.rank}</p>
          <p className="verdict__fact-label">
            {model.worst.id} · of {model.of}
          </p>
        </div>
      </div>

      <ul className="verdict">
        {model.rows.map((row) => (
          <li className="verdict__row" key={row.id} data-verdict={row.id}>
            <span className="verdict__name">{row.id}</span>
            <svg
              className="verdict__track"
              width="100%"
              height={model.rowHeight}
              aria-hidden="true"
              focusable="false"
            >
              <line
                className="verdict__centre"
                x1="0"
                y1={model.rowHeight / 2}
                x2="100%"
                y2={model.rowHeight / 2}
              />
              {row.points.map((point, index) => (
                <circle
                  className="verdict__dot"
                  key={`${point.rank}-${index}`}
                  cx={`${point.xPct}%`}
                  cy={model.rowHeight / 2 + point.dy}
                  r="2.4"
                />
              ))}
              <circle
                className="verdict__marker"
                data-rank={row.rank}
                cx={`${row.indiaXPct}%`}
                cy={model.rowHeight / 2}
                r="5.5"
              >
                <title>{`India: rank ${row.rank} of ${row.of}`}</title>
              </circle>
            </svg>
            <span className="verdict__rank">
              <span className="verdict__rank-value" data-rank={row.rank}>
                {row.rank}
              </span>
              <span className="verdict__of"> of {row.of}</span>
            </span>
          </li>
        ))}

        <li className="verdict__axis" aria-hidden="true">
          <span />
          <svg className="verdict__axis-track" width="100%" height="26">
            <line className="chart__axis" x1="0" y1="0" x2="100%" y2="0" />
            {model.ticks.map((tick) => (
              <g key={tick.label}>
                <line
                  className="chart__tick"
                  x1={`${tick.pct}%`}
                  y1="0"
                  x2={`${tick.pct}%`}
                  y2="5"
                />
                <text
                  className="chart__tick-label"
                  x={`${tick.pct}%`}
                  y="19"
                  textAnchor="middle"
                >
                  {tick.label}
                </text>
              </g>
            ))}
          </svg>
          <span className="verdict__of">rank 1 = best</span>
        </li>
      </ul>

      <p className="verdict__key">
        <span className="verdict__key-dot" aria-hidden="true" /> India ·{' '}
        <span className="verdict__key-strip" aria-hidden="true" /> the other {model.of - 1}{' '}
        countries’ ranks in that pillar
      </p>
    </div>
  );
}
