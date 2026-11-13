import { useEffect, useMemo, useState } from 'react';
import { readScaleParam, SCALE_EVENT, methodLabel } from '../lib/scale';
import type { PillarLite, ScaleScores, ScoreRow, SortKey, SortState } from '../lib/types';
import RankingsTable from './RankingsTable';
import RankingsToolbar from './RankingsToolbar';

interface RankingsExplorerProps {
  datasets: Record<string, ScaleScores>;
  scaleIds: string[];
  defaultScale: string;
  edition: string;
  pillars: PillarLite[];
  caption: string;
}

function matches(row: ScoreRow, query: string): boolean {
  const value = query.trim().toLowerCase();
  if (value.length === 0) return true;
  return (
    row.shortName.toLowerCase().includes(value) ||
    row.country.toLowerCase().includes(value) ||
    row.iso3.toLowerCase().includes(value)
  );
}

function sortRows(rows: ScoreRow[], sort: SortState): ScoreRow[] {
  const factor = sort.dir === 'asc' ? 1 : -1;
  return [...rows].sort((a, b) => {
    if (sort.key === 'country') {
      return (
        factor *
          (a.shortName || a.country).localeCompare(b.shortName || b.country, 'en') ||
        a.rank - b.rank
      );
    }
    const left = sort.key === 'rank' ? a.rank : a.overall;
    const right = sort.key === 'rank' ? b.rank : b.overall;
    return factor * (left - right) || a.rank - b.rank;
  });
}

export default function RankingsExplorer({
  datasets,
  scaleIds,
  defaultScale,
  edition,
  pillars,
  caption,
}: RankingsExplorerProps) {
  const [scale, setScale] = useState(defaultScale);
  const [mode, setMode] = useState<'rank' | 'score'>('rank');
  const [query, setQuery] = useState('');
  const [showPillars, setShowPillars] = useState(false);
  const [sort, setSort] = useState<SortState>({ key: 'rank', dir: 'asc' });
  const [announcement, setAnnouncement] = useState('');

  const data = datasets[scale] ?? datasets[defaultScale];
  // The movement column is measured against min–max whenever it is present.
  const baselineId = scaleIds.includes('full_minmax') ? 'full_minmax' : defaultScale;
  const movementRanks = useMemo(
    () =>
      Object.fromEntries(
        (datasets[baselineId]?.scores ?? []).map((row) => [row.iso3, row.rank]),
      ),
    [datasets, baselineId],
  );

  // The URL is the source of truth for the scale, so a view survives reload
  // and can be shared (the same rule the IA spec sets for accordion state).
  useEffect(() => {
    setScale(readScaleParam(window.location.search, scaleIds, defaultScale));

    function onPopState() {
      setScale(readScaleParam(window.location.search, scaleIds, defaultScale));
    }
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [scaleIds, defaultScale]);

  const filtered = useMemo(
    () => data.scores.filter((row) => matches(row, query)),
    [data, query],
  );

  const sorted = useMemo(() => sortRows(filtered, sort), [filtered, sort]);

  function chooseScale(next: string) {
    setScale(next);
    const url = new URL(window.location.href);
    if (next === defaultScale) {
      url.searchParams.delete('scale');
    } else {
      url.searchParams.set('scale', next);
    }
    window.history.replaceState({}, '', url);
    window.dispatchEvent(new CustomEvent(SCALE_EVENT, { detail: { scale: next } }));
    setAnnouncement(
      `Showing ${methodLabel(next)} scores. The ranks change with the scale; the Rank vs min–max column shows the movement.`,
    );
  }

  function chooseQuery(next: string) {
    setQuery(next);
    const count = data.scores.filter((row) => matches(row, next)).length;
    setAnnouncement(`${count} of ${data.scores.length} countries shown.`);
  }

  function chooseSort(key: SortKey) {
    const dir =
      sort.key === key ? (sort.dir === 'asc' ? 'desc' : 'asc') : key === 'score' ? 'desc' : 'asc';
    const next: SortState = { key, dir };
    setSort(next);
    const direction =
      key === 'country'
        ? dir === 'asc'
          ? 'A to Z'
          : 'Z to A'
        : key === 'rank'
          ? dir === 'asc'
            ? 'best rank first'
            : 'lowest rank first'
          : dir === 'desc'
            ? 'highest first'
            : 'lowest first';
    setAnnouncement(
      `Sorted by ${key === 'score' ? 'score' : key}, ${direction}, ${filtered.length} countries.`,
    );
  }

  return (
    <section aria-labelledby="rankings-heading">
      <h2 id="rankings-heading" className="sr-only">
        Rankings
      </h2>

      <RankingsToolbar
        query={query}
        onQuery={chooseQuery}
        visible={filtered.length}
        total={data.scores.length}
        mode={mode}
        onMode={setMode}
        scale={scale}
        scaleIds={scaleIds}
        onScale={chooseScale}
        showPillars={showPillars}
        onShowPillars={setShowPillars}
        caption={caption}
      />

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </p>

      <RankingsTable
        rows={sorted}
        allCount={data.scores.length}
        edition={edition}
        pillars={pillars}
        median={data.median}
        mode={mode}
        showPillars={showPillars}
        sort={sort}
        onSort={chooseSort}
        scale={scale}
        defaultScale={defaultScale}
        baselineRanks={scale === baselineId ? null : movementRanks}
      />
    </section>
  );
}
