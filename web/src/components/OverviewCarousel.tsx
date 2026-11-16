import { useCallback, useEffect, useState } from 'react';
import { paneAnnouncement, readPaneParam, writePaneParam } from '../lib/pane';
import { methodLabel, methodShortLabel, readScaleParam, SCALE_EVENT, writeScaleParam } from '../lib/scale';
import type { PaneModel } from '../lib/overview-types';
import FieldChart from './overview/FieldChart';
import CompositionChart from './overview/CompositionChart';
import IndiaChart from './overview/IndiaChart';
import MovementChart from './overview/MovementChart';
import PaneTable from './overview/PaneTable';
import ScaleMovementChart from './overview/ScaleMovementChart';
import ScatterChart from './overview/ScatterChart';
import Top15Chart from './overview/Top15Chart';

interface OverviewCarouselProps {
  /** One eight-pane block per scaling method, built at build time. */
  panes: Record<string, PaneModel[]>;
  methods: string[];
  defaultMethod: string;
  label: string;
}

function Chevron({ direction }: { direction: 'prev' | 'next' }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d={direction === 'prev' ? 'M11.5 3.5 6 9l5.5 5.5' : 'M6.5 3.5 12 9l-5.5 5.5'}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * One pane at a time — not a scroll strip. The active pane is the only one
 * rendered visible; the other seven stay in the DOM, hidden, so every pane's
 * table fallback is there without JavaScript and nothing scrolls sideways.
 *
 * The scale toggle swaps one whole build-time block for another: the island
 * chooses, it never computes. Panes 1–5 and 7–8 follow the toggle; pane 6
 * compares the two methods and says so.
 *
 * `?pane=` and `?scale=` are the shareable state (`?scale=` follows the same
 * rule on the rankings page). Changing either writes it with `replaceState`,
 * which keeps the back button meaning "leave the overview", not "undo a pane".
 */
export default function OverviewCarousel({
  panes: panesByMethod,
  methods,
  defaultMethod,
  label,
}: OverviewCarouselProps) {
  const [index, setIndex] = useState(0);
  const [scale, setScale] = useState(defaultMethod);
  const [announcement, setAnnouncement] = useState('');

  const panes = panesByMethod[scale] ?? panesByMethod[defaultMethod];
  const total = panes.length;
  const active = panes[index];

  const goTo = useCallback(
    (next: number) => {
      const clamped = Math.min(total, Math.max(1, next)) - 1;
      setIndex(clamped);
      const url = writePaneParam(new URL(window.location.href), clamped + 1);
      window.history.replaceState({}, '', url);
    },
    [total],
  );

  const chooseScale = useCallback(
    (next: string) => {
      setScale(next);
      // Keep the pane: `?pane=3&scale=minmax` is a shareable view.
      const url = writeScaleParam(new URL(window.location.href), next, defaultMethod);
      window.history.replaceState({}, '', url);
      // The footer's method note tracks the active scale.
      window.dispatchEvent(new CustomEvent(SCALE_EVENT, { detail: { scale: next } }));
      setAnnouncement(`Showing ${methodLabel(next)} scores. Every pane follows except pane 6, which always compares both methods.`);
    },
    [defaultMethod],
  );

  // Restore pane and scale from the URL, the same way `?scale=` is restored on
  // the rankings page. The default scale is never written, so `?scale=z`
  // normalises to absent.
  useEffect(() => {
    setIndex(readPaneParam(window.location.search, total) - 1);
    const restored = readScaleParam(window.location.search, methods, defaultMethod);
    setScale(restored);
    if (restored === defaultMethod) {
      const url = writeScaleParam(new URL(window.location.href), restored, defaultMethod);
      if (url.href !== window.location.href) {
        window.history.replaceState({}, '', url);
      }
    }

    function onPopState() {
      setIndex(readPaneParam(window.location.search, total) - 1);
      setScale(readScaleParam(window.location.search, methods, defaultMethod));
    }
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [total, methods, defaultMethod]);

  // Announce pane changes. Deliberately not on first paint: a page load is
  // not a carousel move, and the heading is already read.
  useEffect(() => {
    if (announcement === '' && index === 0) return;
    setAnnouncement(paneAnnouncement(index + 1, total, panes[index].title));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, total]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || target.isContentEditable)
      ) {
        return;
      }

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          goTo(index);
          break;
        case 'ArrowRight':
          event.preventDefault();
          goTo(index + 2);
          break;
        case 'Home':
          event.preventDefault();
          goTo(1);
          break;
        case 'End':
          event.preventDefault();
          goTo(total);
          break;
        default:
          break;
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [goTo, index, total]);

  return (
    <div
      className="carousel"
      role="group"
      aria-roledescription="carousel"
      aria-label={label}
    >
      <div className="carousel__bar">
        <p className="carousel__eyebrow">
          Eight views of one index
        </p>
        <div className="carousel__scale-group">
          <span className="carousel__scale-label" aria-hidden="true">
            Scale
          </span>
          <fieldset className="segmented carousel__scale">
            <legend>Scale</legend>
            {methods.map((id) => (
              <label className="segmented__option" key={id}>
                <input
                  type="radio"
                  name="overview-scale"
                  value={id}
                  checked={scale === id}
                  onChange={() => chooseScale(id)}
                />
                <span>{methodShortLabel(id)}</span>
              </label>
            ))}
          </fieldset>
        </div>
        <div className="carousel__nav">
          <button
            type="button"
            className="carousel__button"
            onClick={() => goTo(index)}
            disabled={index === 0}
            aria-label="Previous pane"
          >
            <Chevron direction="prev" />
          </button>
          <span className="carousel__count" aria-hidden="true">
            {index + 1} / {total}
          </span>
          <button
            type="button"
            className="carousel__button"
            onClick={() => goTo(index + 2)}
            disabled={index === total - 1}
            aria-label="Next pane"
          >
            <Chevron direction="next" />
          </button>
        </div>
      </div>

      <div className="carousel__stage">
        {panes.map((pane, paneIndex) => {
          const hidden = paneIndex !== index;
          return (
            <section
              key={pane.number}
              className="carousel__pane"
              data-pane={pane.number}
              data-active={hidden ? undefined : 'true'}
              hidden={hidden}
              aria-labelledby={`pane-title-${pane.number}`}
            >
              <header className="pane__head">
                <p className="pane__number">{String(pane.number).padStart(2, '0')}</p>
                <h2 className="pane__title" id={`pane-title-${pane.number}`}>
                  {pane.title}
                </h2>
                <p className="pane__what">{pane.what}</p>
              </header>

              <figure className="pane__figure">
                {pane.chart.kind === 'field' && <FieldChart model={pane.chart} />}
                {pane.chart.kind === 'top15' && <Top15Chart model={pane.chart} />}
                {pane.chart.kind === 'composition' && (
                  <CompositionChart model={pane.chart} />
                )}
                {pane.chart.kind === 'india' && <IndiaChart model={pane.chart} />}
                {pane.chart.kind === 'movement' && <MovementChart model={pane.chart} />}
                {pane.chart.kind === 'scaleMovement' && (
                  <ScaleMovementChart model={pane.chart} />
                )}
                {(pane.chart.kind === 'sizeScore' || pane.chart.kind === 'coverage') && (
                  <ScatterChart model={pane.chart} />
                )}
                {pane.chart.kind === 'placeholder' && (
                  <div className="pane__placeholder">
                    <p className="pane__placeholder-line">{pane.chart.note}</p>
                    {pane.chart.detail && (
                      <p className="pane__placeholder-detail">{pane.chart.detail}</p>
                    )}
                  </div>
                )}
                {pane.caption && (
                  <figcaption className="pane__caption">{pane.caption}</figcaption>
                )}
              </figure>

              <details className="pane__table" data-pane-table={pane.number}>
                <summary>View as table</summary>
                {pane.table ? (
                  <PaneTable table={pane.table} />
                ) : (
                  <p className="body-s hint pane__table-fallback">{pane.tableFallback}</p>
                )}
              </details>

              <p className="method-note">{pane.methodNote}</p>
            </section>
          );
        })}
      </div>

      <div className="carousel__dots" role="group" aria-label="Choose a pane">
        {panes.map((pane, paneIndex) => (
          <button
            key={pane.number}
            type="button"
            className="carousel__dot"
            aria-label={`Go to pane ${pane.number}: ${pane.title}`}
            aria-current={paneIndex === index ? 'true' : undefined}
            onClick={() => goTo(paneIndex + 1)}
          >
            <span className="sr-only">{pane.number}</span>
          </button>
        ))}
      </div>

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </p>
    </div>
  );
}
