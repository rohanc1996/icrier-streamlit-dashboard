import { useEffect, useState } from 'react';
import { methodLabel, readScaleParam, SCALE_EVENT } from '../lib/scale';

interface MethodNoteProps {
  edition: string;
  countries: number;
  leaves: number;
  scaleIds: string[];
  defaultScale: string;
}

/**
 * Footnotes strip (IA §8): edition, active scaling method, N, rounding.
 * The method is read from the URL so the note always names the scale that
 * produced the numbers on screen.
 */
export default function MethodNote({
  edition,
  countries,
  leaves,
  scaleIds,
  defaultScale,
}: MethodNoteProps) {
  const [scale, setScale] = useState(defaultScale);

  useEffect(() => {
    setScale(readScaleParam(window.location.search, scaleIds, defaultScale));

    function fromUrl() {
      setScale(readScaleParam(window.location.search, scaleIds, defaultScale));
    }
    function fromEvent(event: Event) {
      const detail = (event as CustomEvent<{ scale?: string }>).detail;
      if (detail?.scale && scaleIds.includes(detail.scale)) setScale(detail.scale);
    }

    window.addEventListener('popstate', fromUrl);
    window.addEventListener(SCALE_EVENT, fromEvent);
    return () => {
      window.removeEventListener('popstate', fromUrl);
      window.removeEventListener(SCALE_EVENT, fromEvent);
    };
  }, [scaleIds, defaultScale]);

  return (
    <p className="method-note">
      Edition {edition} · {methodLabel(scale)} scaling · {countries} countries ·{' '}
      {leaves} indicators · CHIPS composite shown to 2 decimals; indicator and
      pillar scores to 1 decimal.
    </p>
  );
}
