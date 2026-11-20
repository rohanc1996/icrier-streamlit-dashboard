import { useEffect, useMemo, useState } from 'react';
import { readScaleParam, SCALE_EVENT, methodLabel, movementLabel, otherScale, writeScaleParam } from '../lib/scale';
import {
  GROUP_IDS,
  GROUP_LABELS,
  meta as siteMeta,
  type GroupId,
} from '../lib/site';
import type { PillarLite, ScaleScores, ScoreRow, SortKey, SortState } from '../lib/types';
import RankingsTable from './RankingsTable';
import RankingsToolbar from './RankingsToolbar';

interface RankingsExplorerProps {
  datasets: Record<string, ScaleScores>;
  scaleIds: string[];
  /** The site default (z-score), read from the payload's meta. */
  defaultScale: string;
  /** The scale a country profile opens on, used for outbound links. */
  profileScale: string;
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
  profileScale,
  edition,
  pillars,
  caption,
}: RankingsExplorerProps) {
  const [scale, setScale] = useState(defaultScale);
  const [mode, setMode] = useState<'rank' | 'score'>('rank');
  const [query, setQuery] = useState('');
  const [showPillars, setShowPillars] = useState(false);
  const [sort, setSort] = useState<SortState>({ key: 'rank', dir: 'asc' });
  const [group, setGroup] = useState<GroupId>('all');
  const [custom, setCustom] = useState<string[]>([]);
  const [announcement, setAnnouncement] = useState('');

  const data = datasets[scale] ?? datasets[defaultScale];
  // The movement column always measures against the other method, so it is
  // "Rank vs min–max" while z is active and "Rank vs z" while min–max is.
  const baselineId = otherScale(scaleIds, scale);
  const baselineLabel = baselineId ? movementLabel(baselineId) : null;
  const movementRanks = useMemo(
    () =>
      baselineId
        ? Object.fromEntries(
            (datasets[baselineId]?.scores ?? []).map((row) => [row.iso3, row.rank]),
          )
        : null,
    [datasets, baselineId],
  );

  // The URL is the source of truth for the scale, so a view survives reload
  // and can be shared (the same rule the IA spec sets for accordion state).
  useEffect(() => {
    setScale(readScaleParam(window.location.search, scaleIds, defaultScale));
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('group');
    if (requested && (GROUP_IDS as readonly string[]).includes(requested)) {
      setGroup(requested as GroupId);
    }
    const requestedCustom = (params.get('countries') ?? '')
      .split(',')
      .map((value) => value.trim().toUpperCase())
      .filter((value) => /^[A-Z]{3}$/.test(value));
    if (requestedCustom.length) setCustom(requestedCustom);

    function onPopState() {
      setScale(readScaleParam(window.location.search, scaleIds, defaultScale));
      const next = new URLSearchParams(window.location.search).get('group');
      setGroup(next && (GROUP_IDS as readonly string[]).includes(next) ? (next as GroupId) : 'all');
    }
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [scaleIds, defaultScale]);

  const groupSet = useMemo(() => {
    if (group === 'custom') return new Set(custom);
    const list = siteMeta.groups[group];
    return list ? new Set(list) : null;
  }, [group, custom]);

  const filtered = useMemo(
    () =>
      data.scores.filter(
        (row) => matches(row, query) && (!groupSet || groupSet.has(row.iso3)),
      ),
    [data, query, groupSet],
  );

  const sorted = useMemo(() => sortRows(filtered, sort), [filtered, sort]);

  function chooseScale(next: string) {
    setScale(next);
    // The default leaves the URL alone, so `?scale` is absent unless the
    // non-default method is active. The token is `minmax`, not `full_minmax`.
    const url = writeScaleParam(new URL(window.location.href), next, defaultScale);
    window.history.replaceState({}, '', url);
    window.dispatchEvent(new CustomEvent(SCALE_EVENT, { detail: { scale: next } }));
    const against = otherScale(scaleIds, next);
    setAnnouncement(
      `Showing ${methodLabel(next)} scores. The ranks change with the scale;` +
        (against
          ? ` the Rank vs ${movementLabel(against)} column shows the movement.`
          : '.'),
    );
  }

  function chooseGroup(next: GroupId) {
    setGroup(next);
    const url = new URL(window.location.href);
    if (next === 'all') url.searchParams.delete('group');
    else url.searchParams.set('group', next);
    window.history.replaceState({}, '', url);
    const count = data.scores.filter(
      (row) =>
        matches(row, query) &&
        (next === 'custom'
          ? custom.includes(row.iso3)
          : !siteMeta.groups[next] || siteMeta.groups[next]!.includes(row.iso3)),
    ).length;
    setAnnouncement(`${count} of ${data.scores.length} countries shown.`);
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
        group={group}
        onGroup={chooseGroup}
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
        linkScale={profileScale}
        baselineRanks={movementRanks}
        baselineLabel={baselineLabel}
      />
    </section>
  );
}
