/**
 * One round country flag, centred on an exact data position.
 *
 * Shared by every pane that draws flags — the field (pane 1), the podium
 * (pane 2) and both scatters (panes 7–8) — so there is one mark geometry, one
 * `--surface` ring and one mobile shrink rule, not four near-copies.
 *
 * The parent SVG owns the paint order: callers render the marks in the order
 * they should stack, and the last one ends up on top.
 *
 * `label` decides the semantics. When it is given the mark is an interactive
 * image: focusable, named, with a `<title>` and a focus ring, and the per-flag
 * CSS in `FlagSprite.astro` reveals its overlay. When it is omitted the mark is
 * decorative — pane 2 already prints each country's name as text — so it is
 * `aria-hidden` and takes no tab stop.
 */
export const FLAG_RING_WIDTH = 1.5;

export interface FlagMarkProps {
  /** Alpha-2 code: names the sprite symbol and the per-flag CSS class. */
  iso2: string;
  /** Horizontal centre, as a percentage of the SVG width. */
  xPct: number;
  /** Vertical centre, in SVG user units (px). */
  y: number;
  /** Half the flag's edge in px: 9 for 18px marks, 7.5 for 15px. */
  radius: number;
  /** Accessible name. Omit for a decorative flag. */
  label?: string;
  /** `data-*` hooks used by the verifier; spread onto the group. */
  data?: Record<string, string | number | boolean | undefined>;
  /** Outside the selected country group: drawn muted, still reachable. */
  muted?: boolean;
}

export default function FlagMark({
  iso2,
  xPct,
  y,
  radius,
  label,
  data,
  muted = false,
}: FlagMarkProps) {
  const decorative = label === undefined;

  return (
    <g
      {...data}
      className={`flag-mark flag-mark--${iso2}${muted ? ' is-muted' : ''}`}
      tabIndex={decorative ? undefined : 0}
      role={decorative ? undefined : 'img'}
      aria-label={decorative ? undefined : label}
      aria-hidden={decorative ? 'true' : undefined}
    >
      {decorative ? null : <title>{label}</title>}
      {/* The surface disc is the chip edge; the flag is centred on it. */}
      <circle
        className="flag-mark__ring"
        cx={`${xPct}%`}
        cy={y}
        r={radius + FLAG_RING_WIDTH}
      />
      <use
        href={`#flag-${iso2}`}
        x={`${xPct}%`}
        y={y}
        width={radius * 2}
        height={radius * 2}
        transform={`translate(${-radius} ${-radius})`}
      />
      {decorative ? null : (
        <circle
          className="flag-mark__focus"
          cx={`${xPct}%`}
          cy={y}
          r={radius + 3}
        />
      )}
    </g>
  );
}
