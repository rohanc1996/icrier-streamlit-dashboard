interface MissingValueProps {
  /** Full reason, used for the tooltip and the accessible name. */
  detail?: string;
  /** Inline prints the words instead of an em dash (IA §4). */
  variant?: 'cell' | 'inline';
  /** Inline only: print the reason on the next line in 13px muted text. */
  showDetail?: boolean;
}

/**
 * The missing-data primitive: never a blank, never a zero, never red.
 * An em dash with a dotted rule in a cell; the words "Not scored" in prose.
 *
 * No `aria-label` is placed on a bare span (axe's aria-prohibited-attr): the
 * visible text plus a visually-hidden label carries the name instead.
 */
export default function MissingValue({
  detail,
  variant = 'cell',
  showDetail = false,
}: MissingValueProps) {
  const label = detail ? `Not scored — ${detail}` : 'Not scored';

  if (variant === 'inline') {
    return (
      <>
        <span className="missing-label" title={label}>
          Not scored
        </span>
        {showDetail && detail ? <span className="missing-reason">{detail}</span> : null}
      </>
    );
  }

  return (
    <span className="missing" title={label}>
      <span aria-hidden="true">—</span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
