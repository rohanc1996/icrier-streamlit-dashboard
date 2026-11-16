/**
 * The hover/focus reveal for an interactive `FlagMark`: a bigger copy of the
 * flag, a labelled chip, and the sibling the generated CSS in
 * `FlagSprite.astro` targets.
 *
 * These live in a layer that is the **last** element in the parent SVG, because
 * the marks themselves are painted in rank order and partly cover each other;
 * a revealed name has to sit above all of them. `.flag-mark--us:focus` reaches
 * `.flag-overlay--us` through the general sibling combinator. Pure CSS — no
 * script and no pointer events while hidden.
 */
export const OVERLAY_RADIUS = 11;

export interface FlagOverlayProps {
  iso2: string;
  xPct: number;
  y: number;
  /** The same "country, score" text the matching mark announces. */
  label: string;
  /** Baseline of the label, already clamped inside the plot. */
  labelY: number;
  /** True when the text sits to the right of the chip. */
  right: boolean;
  /** The mark's iso3, for the verifier's `[data-overlay]` lookup. */
  iso3: string;
}

export default function FlagOverlay({
  iso2,
  xPct,
  y,
  label,
  labelY,
  right,
  iso3,
}: FlagOverlayProps) {
  return (
    <g
      className={`flag-overlay flag-overlay--${iso2}`}
      data-overlay={iso3}
      aria-hidden="true"
    >
      <circle
        className="flag-overlay__ring"
        cx={`${xPct}%`}
        cy={y}
        r={OVERLAY_RADIUS + 1.5}
      />
      <use
        href={`#flag-${iso2}`}
        x={`${xPct}%`}
        y={y}
        width={OVERLAY_RADIUS * 2}
        height={OVERLAY_RADIUS * 2}
        transform={`translate(${-OVERLAY_RADIUS} ${-OVERLAY_RADIUS})`}
      />
      <text
        className="flag-overlay__label"
        x={`${xPct}%`}
        y={labelY}
        dx={right ? OVERLAY_RADIUS + 6 : -(OVERLAY_RADIUS + 6)}
        textAnchor={right ? 'start' : 'end'}
      >
        {label}
      </text>
    </g>
  );
}
