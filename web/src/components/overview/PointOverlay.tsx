/**
 * The hover/focus reveal for a plain `PointMark`: a ring around the dot and the
 * same "country, score" label chip a flagged point shows.
 *
 * Lives in the last layer of the parent SVG, like `FlagOverlay`, so a revealed
 * label sits above every mark and every other overlay. The matching sibling
 * rule (`.chart-point--xx:hover ~ .point-overlay--xx`) is generated in
 * `FlagSprite.astro`, because the class suffix follows the data.
 */
export const POINT_OVERLAY_RADIUS = 8;

export interface PointOverlayProps {
  iso3: string;
  xPct: number;
  y: number;
  /** The same "country, score" text the matching point announces. */
  label: string;
  /** Baseline of the label, already clamped inside the plot. */
  labelY: number;
  /** True when the text sits to the right of the dot. */
  right: boolean;
}

export default function PointOverlay({
  iso3,
  xPct,
  y,
  label,
  labelY,
  right,
}: PointOverlayProps) {
  const key = iso3.toLowerCase();

  return (
    <g
      className={`point-overlay point-overlay--${key}`}
      data-overlay={iso3}
      aria-hidden="true"
    >
      <circle
        className="point-overlay__ring"
        cx={`${xPct}%`}
        cy={y}
        r={POINT_OVERLAY_RADIUS}
      />
      <text
        className="point-overlay__label"
        x={`${xPct}%`}
        y={labelY}
        dx={right ? POINT_OVERLAY_RADIUS + 6 : -(POINT_OVERLAY_RADIUS + 6)}
        textAnchor={right ? 'start' : 'end'}
      >
        {label}
      </text>
    </g>
  );
}
