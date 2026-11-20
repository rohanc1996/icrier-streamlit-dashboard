/**
 * One plain country dot, focusable on its exact data position.
 *
 * Pairs with `PointOverlay`: the group's `chart-point--<iso3>` class is what the
 * sibling rule in `FlagSprite.astro` uses to reveal the label in the overlay
 * layer that closes the SVG. The visible dot keeps every `data-*` hook the
 * chart and the verifier already use, so counts and selectors do not change.
 *
 * A transparent hit circle grows the 4px dot to a comfortable pointer target;
 * the focus ring is the visible keyboard indicator, not the browser outline.
 */
export interface PointMarkProps {
  iso3: string;
  /** Horizontal centre, as a percentage of the SVG width. */
  xPct: number;
  /** Vertical centre, in SVG user units (px). */
  y: number;
  /** Radius of the visible dot. */
  radius: number;
  /** Accessible name, e.g. "India, score 66.03". */
  label: string;
  /** The dot's existing class, e.g. `scatter__dot` or `field-chart__dot`. */
  dotClassName: string;
  /** `data-*` hooks spread onto the visible dot, not the group. */
  data?: Record<string, string | number | boolean | undefined>;
  /** Outside the selected country group: drawn muted, still reachable. */
  muted?: boolean;
}

export default function PointMark({
  iso3,
  xPct,
  y,
  radius,
  label,
  dotClassName,
  data,
  muted = false,
}: PointMarkProps) {
  const key = iso3.toLowerCase();
  const hitRadius = Math.max(radius + 5, 9);

  return (
    <g
      className={`chart-point chart-point--${key}${muted ? ' is-muted' : ''}`}
      data-point={iso3}
      data-iso3={iso3}
      tabIndex={0}
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      <circle
        className="chart-point__hit"
        cx={`${xPct}%`}
        cy={y}
        r={hitRadius}
      />
      <circle
        {...data}
        className={dotClassName}
        cx={`${xPct}%`}
        cy={y}
        r={radius}
      />
      <circle
        className="chart-point__focus"
        cx={`${xPct}%`}
        cy={y}
        r={radius + 4}
      />
    </g>
  );
}
