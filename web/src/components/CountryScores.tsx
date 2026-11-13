import { useEffect, useId, useState } from 'react';
import { PARTIAL_DATA_COVERAGE } from '../lib/constants';
import { formatComposite, formatPercent, formatRank } from '../lib/format';
import {
  pillarOpenSlug,
  readOpenParam,
  subPillarOpenSlug,
  writeOpenParam,
} from '../lib/open';
import { methodLabel, readScaleParam } from '../lib/scale';
import type { IndicatorRow, Pillar, ScoreRow, SubPillar } from '../lib/types';
import PillarCard from './PillarCard';
import PillarDetail from './PillarDetail';
import ScoreBar from './ScoreBar';

interface CountryScoresProps {
  rows: Record<string, ScoreRow>;
  indicators: Record<string, IndicatorRow[]>;
  subPillarOf: Record<string, Record<string, number>>;
  medians: Record<string, number>;
  scaleIds: string[];
  defaultScale: string;
  pillars: Pillar[];
  countryCount: number;
  coverageLine: string;
}

function notScoredForPillar(row: ScoreRow, pillarId: string): number {
  return Object.entries(row.subPillars).filter(
    ([key, item]) => key.startsWith(`${pillarId} · `) && item.status !== 'present',
  ).length;
}

/**
 * Method-agnostic profile display: it is handed one row per scaling method and
 * picks the one the URL asks for. It never knows how a score was produced.
 *
 * `?open=` state follows the same rule: the URL is shareable and survives a
 * reload, and it is updated without touching `?scale=`.
 */
export default function CountryScores({
  rows,
  indicators,
  subPillarOf,
  medians,
  scaleIds,
  defaultScale,
  pillars,
  countryCount,
  coverageLine,
}: CountryScoresProps) {
  const [scale, setScale] = useState(defaultScale);
  const [openPillar, setOpenPillar] = useState<string | null>(null);
  const [openSub, setOpenSub] = useState<string | null>(null);
  const rawId = useId();
  const baseId = `profile-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`;

  useEffect(() => {
    function applyUrl() {
      setScale(readScaleParam(window.location.search, scaleIds, defaultScale));
      const target = readOpenParam(window.location.search, pillars);
      setOpenPillar(target?.pillarId ?? null);
      setOpenSub(target?.subKey ?? null);
    }

    applyUrl();
    window.addEventListener('popstate', applyUrl);
    return () => window.removeEventListener('popstate', applyUrl);
  }, [scaleIds, defaultScale, pillars]);

  const row = rows[scale] ?? rows[defaultScale];
  const median = medians[scale] ?? medians[defaultScale];
  const activeIndicators = indicators[scale] ?? indicators[defaultScale];
  const activeSubPillarOf = subPillarOf[scale] ?? subPillarOf[defaultScale];
  const countryName = row.shortName || row.country;
  const partial = row.coverage < PARTIAL_DATA_COVERAGE;

  function writeOpen(value: string | null) {
    const url = writeOpenParam(new URL(window.location.href), value);
    window.history.replaceState({}, '', url);
  }

  function panelIdFor(pillar: Pillar): string {
    return `${baseId}-pillar-${pillar.id.toLowerCase()}`;
  }

  function togglePillar(pillar: Pillar, scrollIntoView = false) {
    const next = openPillar === pillar.id ? null : pillar.id;
    setOpenPillar(next);
    setOpenSub(null);
    writeOpen(next ? pillarOpenSlug(pillar) : null);

    // Pointer users on a narrow screen would otherwise open a panel below the
    // whole card row with nothing visibly changing. Keyboard users keep their
    // focused header in place and Tab into the panel instead.
    if (next && scrollIntoView && window.matchMedia('(max-width: 960px)').matches) {
      requestAnimationFrame(() => {
        const panel = document.getElementById(panelIdFor(pillar));
        if (!panel) return;
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        panel.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      });
    }
  }

  function toggleSub(pillar: Pillar, sub: SubPillar) {
    const nextSub = openSub === sub.key ? null : sub.key;
    setOpenSub(nextSub);
    writeOpen(nextSub ? subPillarOpenSlug(pillar, sub.name) : pillarOpenSlug(pillar));
  }

  return (
    <>
      <div className="country-head">
        <div>
          <p className="body-s hint" style={{ marginBottom: 0 }}>
            Rank {formatRank(row.rank)} of {countryCount} · CHIPS score
          </p>
          <div className="country-head__score">
            <span className="display-xl">{formatComposite(row.overall)}</span>
            <span className="body-s hint">of 100</span>
            {partial && (
              <span
                className="chip chip--partial"
                title={`Coverage ${formatPercent(row.coverage)} — ${row.indicatorsPresent} of ${row.indicatorsTotal} indicators`}
              >
                Partial data
                <span className="sr-only">
                  {' '}
                  — coverage {formatPercent(row.coverage)}, {row.indicatorsPresent} of{' '}
                  {row.indicatorsTotal} indicators
                </span>
              </span>
            )}
          </div>
        </div>
        <p className="body-s hint">{methodLabel(scale)} scale</p>
      </div>

      <div className="country-bar">
        <ScoreBar score={row.overall} median={median} />
      </div>
      <div className="country-bar__scale" aria-hidden="true">
        <span>0</span>
        <span>100</span>
      </div>
      <p className="country-bar__median">World median {formatComposite(median)}</p>

      <p className="body-s country-head__coverage">{coverageLine}</p>

      <section className="pillar-section" aria-labelledby="pillars-heading">
        <h2 id="pillars-heading" className="display-m">
          The five areas
        </h2>
        <p className="body-s hint">
          Weight is shown under each pillar. Open a pillar to see its sub-pillars; open a
          sub-pillar to see its indicators. One pillar stays open at a time.
        </p>
        <div className="pillar-grid">
          {pillars.map((pillar) => {
            const value = row.pillars[pillar.id];
            const panelId = panelIdFor(pillar);
            return (
              <PillarCard
                key={pillar.id}
                pillar={pillar}
                score={value?.score ?? null}
                rank={value?.rank ?? null}
                countryCount={countryCount}
                notScored={notScoredForPillar(row, pillar.id)}
                open={openPillar === pillar.id}
                panelId={panelId}
                onToggle={(scrollIntoView) => togglePillar(pillar, scrollIntoView)}
              />
            );
          })}
        </div>

        <div className="pillar-panels">
          {pillars.map((pillar) => {
            const value = row.pillars[pillar.id];
            return (
              <PillarDetail
                key={pillar.id}
                pillar={pillar}
                open={openPillar === pillar.id}
                panelId={panelIdFor(pillar)}
                countryName={countryName}
                score={value?.score ?? null}
                rank={value?.rank ?? null}
                countryCount={countryCount}
                notScored={notScoredForPillar(row, pillar.id)}
                subPillars={row.subPillars}
                subPillarOf={activeSubPillarOf}
                indicatorRows={activeIndicators}
                openSub={openSub}
                onToggleSub={(sub) => toggleSub(pillar, sub)}
                baseId={baseId}
              />
            );
          })}
        </div>
      </section>
    </>
  );
}
