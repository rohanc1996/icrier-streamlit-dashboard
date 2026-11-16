import type { ScatterChartModel } from '../../lib/overview-types';

/**
 * Panes 7–8: a scatter with a fixed pixel height and percentage x positions,
 * so the plot narrows on a small screen instead of scrolling and the labels
 * stay at a readable size.
 *
 * Pane 7 uses a logarithmic GDP axis: the economies span three orders of
 * magnitude, and a linear axis would pile every country except the largest
 * three into the left margin. Pane 8 marks the countries below 80% coverage
 * and states the unscored-cell count in the pane, not in a footnote.
 */
export default function ScatterChart({ model }: { model: ScatterChartModel }) {
  // yTicks run from 0 (bottom) to the axis maximum (top), so the x axis sits
  // on the first tick, not the last.
  const axisY = model.yTicks[0]?.y ?? 0;
  const topY = model.yTicks[model.yTicks.length - 1]?.y ?? 0;
  const coverage = model.kind === 'coverage';
  const labelled = model.points.filter(
    (point) => point.labelY !== undefined && point.labelXPct !== undefined,
  );

  return (
    <div
      className={`scatter-chart scatter-chart--${model.kind}`}
      role="group"
      aria-label={model.ariaLabel}
    >
      {coverage && (
        <p className="pane__callout">
          <strong>{model.belowThreshold ?? 0}</strong> of {model.points.length} countries sit
          below 80% coverage
          <span className="scatter-chart__callout-note">
            {' '}
            · {model.unscoredCells ?? 0} country × sub-pillar cells are unscored in this
            edition
          </span>
        </p>
      )}

      <svg
        className="scatter-chart__plot"
        width="100%"
        height={model.height}
        aria-hidden="true"
        focusable="false"
      >
        {model.yTicks.map((tick) => (
          <g key={tick.label}>
            <line
              className="scatter__grid"
              x1={`${model.plotLeftPct}%`}
              y1={tick.y}
              x2={`${model.plotRightPct}%`}
              y2={tick.y}
            />
            <text
              className="chart__tick-label"
              x={`${model.plotLeftPct - 1.5}%`}
              y={tick.y + 4}
              textAnchor="end"
            >
              {tick.label}
            </text>
          </g>
        ))}

        <text
          className="chart__axis-title"
          x={`${model.plotLeftPct}%`}
          y="10"
          textAnchor="start"
        >
          CHIPS score
        </text>

        {model.thresholdPct !== undefined && (
          <g>
            <line
              className="scatter__threshold"
              x1={`${model.thresholdPct}%`}
              y1={topY}
              x2={`${model.thresholdPct}%`}
              y2={axisY}
            />
            <text
              className="scatter__threshold-label"
              x={`${model.thresholdPct}%`}
              y={topY - 3}
              textAnchor="middle"
            >
              80%
            </text>
          </g>
        )}

        {model.points.map((point) => (
          <circle
            key={point.iso3}
            data-scatter={point.iso3}
            data-below={point.belowThreshold ? 'true' : undefined}
            className={`scatter__dot${
              point.belowThreshold ? ' scatter__dot--below' : ''
            }`}
            cx={`${point.xPct}%`}
            cy={point.y}
            r={point.belowThreshold ? 5 : 4}
          />
        ))}

        {labelled.map((point) => (
          <text
            key={`label-${point.iso3}`}
            className="chart__label chart__label--halo"
            x={`${point.labelXPct}%`}
            y={point.labelY}
            textAnchor={point.labelAnchor ?? 'middle'}
          >
            {point.label}
          </text>
        ))}

        <line
          className="chart__axis"
          x1={`${model.plotLeftPct}%`}
          y1={axisY}
          x2={`${model.plotRightPct}%`}
          y2={axisY}
        />
        {model.xTicks.map((tick, index) => (
          <g key={tick.label}>
            <line
              className="chart__tick"
              x1={`${tick.pct}%`}
              y1={axisY}
              x2={`${tick.pct}%`}
              y2={axisY + 5}
            />
            <text
              className="chart__tick-label"
              x={`${tick.pct}%`}
              y={axisY + 19}
              textAnchor={
                index === 0 ? 'start' : index === model.xTicks.length - 1 ? 'end' : 'middle'
              }
            >
              {tick.label}
            </text>
          </g>
        ))}
        <text
          className="chart__axis-title"
          x={`${(model.plotLeftPct + model.plotRightPct) / 2}%`}
          y={axisY + 36}
          textAnchor="middle"
        >
          {coverage ? 'share of the indicator set present' : 'GDP 2025, current US$ (log scale)'}
        </text>
      </svg>

      {coverage && (
        <p className="scatter-chart__key">
          <span className="scatter-chart__swatch scatter-chart__swatch--below" aria-hidden="true" />
          below 80% coverage
          <span className="scatter-chart__swatch scatter-chart__swatch--other" aria-hidden="true" />
          80% or more
        </p>
      )}
    </div>
  );
}
