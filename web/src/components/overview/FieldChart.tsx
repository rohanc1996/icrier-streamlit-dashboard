import { formatComposite } from '../../lib/format';
import type { FieldChartModel, FieldPointModel } from '../../lib/overview-types';
import FlagMark from './FlagMark';
import FlagOverlay from './FlagOverlay';
import PointMark from './PointMark';
import PointOverlay from './PointOverlay';

/** Flag radius, in px, at desktop size: an 18px flag. */
const FLAG_RADIUS = 9;

/**
 * Beeswarm of every CHIPS score. Positions are computed at build time; the
 * x axis is expressed in percentages so the plot compresses rather than
 * scrolls, while the text stays at a readable pixel size.
 *
 * The ten best scores in the active method are flags, not dots — the same
 * treatment the scatters get, from the same components. They are painted rank
 * 10 first and rank 1 last so the best score is on top; the ones underneath
 * stay reachable because every flag is focusable and a CSS sibling rule
 * reveals its labelled overlay. Everything below the top 10 stays a dot.
 *
 * This plot is denser than the scatters, but the flagged countries are the
 * high-score outliers at the right-hand end, so the flags sit clear of the
 * central cloud. Their positions are exact, not nudged to avoid the mass.
 */
export default function FieldChart({ model }: { model: FieldChartModel }) {
  const india = model.points.find((point) => point.isIndia);
  const dots = model.points.filter(
    (point) => !point.flagRank || !point.flagIso2,
  );
  // Document order is paint order. Highest rank number first → rank 1 last.
  const flags = model.points
    .filter(
      (point): point is FieldPointModel & { flagRank: number; flagIso2: string } =>
        typeof point.flagRank === 'number' && typeof point.flagIso2 === 'string',
    )
    .sort((a, b) => b.flagRank - a.flagRank);

  const markName = (point: FieldPointModel) =>
    `${point.label}, score ${formatComposite(point.score)}`;

  return (
    <svg
      className="field-chart"
      width="100%"
      height={model.height}
      role="group"
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

      {dots.map((point) => (
        <PointMark
          key={point.iso3}
          iso3={point.iso3}
          xPct={point.xPct}
          y={point.cy}
          radius={point.isIndia ? 5.5 : 4.5}
          label={markName(point)}
          dotClassName={
            point.isIndia ? 'field-chart__dot field-chart__dot--india' : 'field-chart__dot'
          }
          muted={point.inSelection === false}
          data={{
            'data-dot': point.iso3,
            'data-field': point.iso3,
            'data-score': point.score,
          }}
        />
      ))}

      {india && (
        <>
          {/* The ring has to clear the 18px flag, so it grows when India is
              in the flagged group and keeps the tighter dot halo when not. */}
          <circle
            className="field-chart__ring"
            cx={`${india.xPct}%`}
            cy={india.cy}
            r={india.flagIso2 ? 12 : 9}
          />
          <text
            className="chart__label chart__label--halo"
            x={`${india.xPct}%`}
            y={india.cy - (india.flagIso2 ? 18 : 15)}
            textAnchor="middle"
          >
            India
          </text>
        </>
      )}

      {flags.map((point) => (
        <FlagMark
          key={point.iso3}
          iso2={point.flagIso2}
          xPct={point.xPct}
          y={point.cy}
          radius={FLAG_RADIUS}
          label={markName(point)}
          muted={point.inSelection === false}
          data={{
            'data-field': point.iso3,
            'data-iso3': point.iso3,
            'data-flag-rank': point.flagRank,
            'data-score': point.score,
          }}
        />
      ))}

      {/* Last in the SVG on purpose: the revealed labels sit above every mark. */}
      {dots.map((point) => (
        <PointOverlay
          key={`point-overlay-${point.iso3}`}
          iso3={point.iso3}
          xPct={point.xPct}
          y={point.cy}
          label={markName(point)}
          right={point.xPct <= 74}
          labelY={Math.max(12, Math.min(model.height - 6, point.cy + 4))}
        />
      ))}
      {flags.map((point) => (
        <FlagOverlay
          key={`overlay-${point.iso3}`}
          iso2={point.flagIso2}
          xPct={point.xPct}
          y={point.cy}
          label={markName(point)}
          iso3={point.iso3}
          right={point.xPct <= 74}
          labelY={Math.max(12, Math.min(model.height - 6, point.cy + 4))}
        />
      ))}
    </svg>
  );
}
