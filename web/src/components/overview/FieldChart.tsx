import type { FieldChartModel } from '../../lib/overview-types';

/**
 * Beeswarm of every CHIPS score. Positions are computed at build time; the
 * x axis is expressed in percentages so the plot compresses rather than
 * scrolls, while the text stays at a readable pixel size.
 */
export default function FieldChart({ model }: { model: FieldChartModel }) {
  const india = model.points.find((point) => point.isIndia);

  return (
    <svg
      className="field-chart"
      width="100%"
      height={model.height}
      role="img"
      aria-label={model.ariaLabel}
    >
      <line
        className="chart__axis"
        x1="0"
        y1={model.axisY}
        x2="100%"
        y2={model.axisY}
      />

      {model.ticks.map((tick) => (
        <g key={tick.label}>
          <line
            className="chart__tick"
            x1={`${tick.pct}%`}
            y1={model.axisY}
            x2={`${tick.pct}%`}
            y2={model.axisY + 5}
          />
          <text
            className="chart__tick-label"
            x={`${tick.pct}%`}
            y={model.axisY + 19}
            textAnchor="middle"
          >
            {tick.label}
          </text>
        </g>
      ))}

      <line
        className="field-chart__median"
        x1={`${model.medianPct}%`}
        y1={14}
        x2={`${model.medianPct}%`}
        y2={model.axisY}
      />
      <text
        className="chart__label"
        x={`${model.medianPct}%`}
        y={12}
        textAnchor="middle"
      >
        Median {model.medianLabel}
      </text>

      {model.points.map((point) => (
        <circle
          key={point.iso3}
          data-dot={point.iso3}
          data-score={point.score}
          className={
            point.isIndia ? 'field-chart__dot field-chart__dot--india' : 'field-chart__dot'
          }
          cx={`${point.xPct}%`}
          cy={point.cy}
          r={point.isIndia ? 5.5 : 4.5}
        />
      ))}

      {india && (
        <>
          <circle
            className="field-chart__ring"
            cx={`${india.xPct}%`}
            cy={india.cy}
            r={9}
          />
          <text
            className="chart__label chart__label--halo"
            x={`${india.xPct}%`}
            y={india.cy - 15}
            textAnchor="middle"
          >
            India
          </text>
        </>
      )}
    </svg>
  );
}
