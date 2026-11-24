import { useCallback, useEffect, useMemo, useState } from 'react';
import FilterBar from './FilterBar';
import CompositionChart from './overview/CompositionChart';
import FieldChart from './overview/FieldChart';
import PaneTable from './overview/PaneTable';
import RankBars from './overview/RankBars';
import RankTracker from './overview/RankTracker';
import RobustnessTable from './overview/RobustnessTable';
import ScatterChart from './overview/ScatterChart';
import Verdicts from './overview/Verdicts';
import {
  BASIS_LABELS,
  DEFAULT_FILTERS,
  DEFAULT_METHOD,
  GROUP_LABELS,
  METHOD_LABELS,
  buildCompositionModel,
  buildFieldModel,
  buildRankBars,
  buildSizeScatter,
  buildVerdictMarks,
  compositionTable,
  meta,
  payload,
  rankBarTable,
  readFilters,
  selectionIso3s,
  selectionSummary,
  sizeTable,
  trackerBlock,
  verdictTable,
  writeFilters,
  type Filters,
  type TableModel,
} from '../lib/site';
import { formatComposite, formatRank } from '../lib/format';

interface OverviewExplorerProps {
  label: string;
}

const PANE_TITLES = [
  'The field',
  'Every score, ranked',
  'Anatomy of a score',
  'Five verdicts',
  'Rank tracker',
  'Two scales, one index',
  'Scale and score',
];

const PANE_WHATS = [
  'Every scored country at once, with the edition median marked.',
  'All countries on one score axis; choose how many rows to show.',
  'Each score split into its five weighted pillar contributions.',
  'The selected country’s rank inside each pillar.',
  'Ranks across editions for countries scored in every one of them.',
  'Where min–max and z-score put the same country, sorted by the size of the difference.',
  `GDP ${meta.gdpYear} against the CHIPS score, on a log axis.`,
];

const TABLES = ['View data', 'View data', 'View data', 'View data', 'Ranks table', 'Sortable table', 'View data'];

const CAVEATS = [
  'What it does not support: comparing these scores with another edition.',
  'Ranks are positions in the published field, not a grade.',
  'Contributions reconstruct the score; they are not a re-weighting.',
  'A pillar rank is not the overall rank.',
  'Ranks only — the indices changed between editions, so scores are not compared.',
  'Only the composite moves; individual indicator ranks do not.',
  'The Absolute edition scores volumes, so size and score are partly related by construction.',
];

function useFilters() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  useEffect(() => {
    const apply = () => setFilters(readFilters(window.location.search));
    apply();
    window.addEventListener('popstate', apply);
    return () => window.removeEventListener('popstate', apply);
  }, []);

  const update = useCallback((next: Filters) => {
    setFilters(next);
    const url = writeFilters(new URL(window.location.href), next);
    window.history.replaceState({}, '', url);
  }, []);

  return { filters, update };
}

export default function OverviewExplorer({ label }: OverviewExplorerProps) {
  const { filters, update } = useFilters();
  const [compositionTop, setCompositionTop] = useState('all');
  const [announcement, setAnnouncement] = useState('');

  const edition = payload.editions[filters.year] ?? {};
  const basis = edition[filters.basis] ? filters.basis : Object.keys(edition)[0];
  const block = edition[basis];
  const method = block?.methods[filters.method] ?? block?.methods[DEFAULT_METHOD];
  const selected = useMemo(() => selectionIso3s(filters), [filters]);

  const groupLabel = GROUP_LABELS[filters.group] ?? filters.group;
  const summary = selectionSummary(
    filters,
    METHOD_LABELS[filters.method] ?? filters.method,
  );

  const activePane = filters.pane;

  function goTo(next: number) {
    const clamped = Math.min(PANE_TITLES.length, Math.max(1, next));
    update({ ...filters, pane: clamped });
  }

  useEffect(() => {
    if (activePane === 1) return;
    setAnnouncement(`Pane ${activePane} of ${PANE_TITLES.length}: ${PANE_TITLES[activePane - 1]}`);
  }, [activePane]);

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
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goTo(activePane - 1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        goTo(activePane + 1);
      } else if (event.key === 'Home') {
        event.preventDefault();
        goTo(1);
      } else if (event.key === 'End') {
        event.preventDefault();
        goTo(PANE_TITLES.length);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  });

  if (!block || !method) {
    return (
      <p className="body-s hint">
        No data block for {filters.year} / {filters.basis}. Regenerate
        `data/derived/web/editions.json`.
      </p>
    );
  }

  const fieldModel = buildFieldModel(method, selected);
  const rankBars = buildRankBars(method);
  const compositionModel = buildCompositionModel(method);
  const verdictCountry =
    filters.compare[0] && method.verdicts.countries[filters.compare[0]]
      ? filters.compare[0]
      : method.field.values.find((row) => row.iso3 === 'IND' && row.score !== null)?.iso3 ??
        method.field.values.find((row) => row.score !== null)?.iso3 ??
        'IND';
  const verdicts = buildVerdictMarks(method, verdictCountry);
  const scatter = buildSizeScatter(method, selected);
  const tracker = trackerBlock(filters.method, filters.years);
  const robustness = block.robustness;
  const totalPool = block.countryCount;

  const rankRows = selected
    ? rankBars.rows.filter((row) => selected.has(row.iso3))
    : rankBars.rows;
  const compositionRows = selected
    ? compositionModel.rows.filter((row) => selected.has(row.iso3))
    : compositionModel.rows;
  const shownComposition =
    compositionTop === 'all'
      ? compositionRows
      : compositionRows.slice(0, Number(compositionTop));

  const panes: React.ReactNode[] = [
    <figure className="pane__figure" key="field">
      <FieldChart model={fieldModel} />
      <figcaption className="pane__caption">
        Scores are 0–100; the median is where the middle of the field sits, not a
        target. Countries outside the selected group are muted, not removed.
        {' '}
        {CAVEATS[0]}
      </figcaption>
      <Disclosure table={{
        caption: `All ${method.field.values.length} CHIPS scores.`,
        columns: ['Rank', 'Country', 'CHIPS score'],
        numericColumns: [0, 2],
        rows: method.field.values
          .filter((row) => row.score !== null)
          .map((row) => [
            formatRank(row.rank),
            (row.shortName || row.country),
            formatComposite(row.score),
          ]),
        note: 'Scores 0–100, two decimals. Ranks ignore the group filter.',
      }} label={TABLES[0]} />
    </figure>,

    <figure className="pane__figure" key="ranks">
      <RankBars
        rows={rankBars.rows}
        max={rankBars.max}
        selected={selected}
        compare={filters.compare}
        label={groupLabel === 'All countries' ? 'countries' : groupLabel}
      />
      <figcaption className="pane__caption">
        The default is every country in the selected group — no cut-off unless you
        choose one. {CAVEATS[1]}
      </figcaption>
      <Disclosure table={rankBarTable(rankRows, groupLabel)} label={TABLES[1]} />
    </figure>,

    <figure className="pane__figure" key="composition">
      <div className="pane-control">
        <label htmlFor="composition-count">Show</label>
        <select
          id="composition-count"
          value={compositionTop}
          onChange={(event) => setCompositionTop(event.target.value)}
        >
          <option value="all">All countries</option>
          <option value="25">Top 25</option>
          <option value="10">Top 10</option>
        </select>
        <span className="micro hint">
          {shownComposition.length} of {compositionRows.length}
        </span>
      </div>
      <CompositionChart model={{ ...compositionModel, rows: shownComposition }} />
      <figcaption className="pane__caption">
        A decomposition, not an illustration: the five contributions sum to the
        score. {CAVEATS[2]}
      </figcaption>
      <Disclosure table={compositionTable(compositionModel)} label={TABLES[2]} />
    </figure>,

    <figure className="pane__figure" key="verdicts">
      {verdicts ? (
        <Verdicts
          country={verdicts.country}
          marks={verdicts.marks}
          best={verdicts.best}
          worst={verdicts.worst}
        />
      ) : (
        <p className="hint">No pillar verdicts for this country in this edition.</p>
      )}
      <figcaption className="pane__caption">
        Pick a country in the geography controls; the first comparison country is
        the profile shown here. {CAVEATS[3]}
      </figcaption>
      {verdicts && (
        <Disclosure
          table={verdictTable(
            verdicts.marks,
            verdicts.country,
            method.verdicts.countries[verdictCountry]?.rank ?? null,
          )}
          label={TABLES[3]}
        />
      )}
    </figure>,

    <figure className="pane__figure" key="tracker">
      {tracker ? (
        <RankTracker
          block={tracker}
          selected={selected}
          compare={filters.compare}
          total={totalPool}
        />
      ) : (
        <p className="hint">
          Select at least two years to open the rank tracker. Ranks are only
          compared within an edition.
        </p>
      )}
      <figcaption className="pane__caption">{CAVEATS[4]}</figcaption>
    </figure>,

    <figure className="pane__figure" key="robustness">
      <RobustnessTable rows={robustness} selected={selected} compare={filters.compare} />
      <figcaption className="pane__caption">{CAVEATS[5]}</figcaption>
    </figure>,

    <figure className="pane__figure" key="size">
      {scatter ? (
        <ScatterChart model={scatter} />
      ) : (
        <p className="hint">No GDP join for this edition.</p>
      )}
      <figcaption className="pane__caption">
        GDP is fixed at {meta.gdpYear}; it does not follow the year selector.
        {' '}
        {CAVEATS[6]}
      </figcaption>
      <Disclosure table={sizeTable(method)} label={TABLES[6]} />
    </figure>,
  ];

  return (
    <div
      className="carousel"
      role="group"
      aria-roledescription="carousel"
      aria-label={label}
    >
      <FilterBar
        filters={filters}
        onChange={update}
        onReset={() => update({ ...DEFAULT_FILTERS })}
        summary={summary}
      />

      <div className="carousel__bar">
        <p className="carousel__eyebrow">Seven views of one index</p>
        <p className="carousel__status">
          {BASIS_LABELS[basis]} · {[...filters.years].sort().join('–')} ·{' '}
          {groupLabel} · {METHOD_LABELS[filters.method]}
          {filters.years.length > 1 ? ` · single-edition panes show ${filters.year}` : ''}
        </p>
        <div className="carousel__nav">
          <button
            type="button"
            className="carousel__button"
            onClick={() => goTo(activePane - 1)}
            disabled={activePane === 1}
            aria-label="Previous pane"
          >
            ‹
          </button>
          <span className="carousel__count" aria-hidden="true">
            {activePane} / {PANE_TITLES.length}
          </span>
          <button
            type="button"
            className="carousel__button"
            onClick={() => goTo(activePane + 1)}
            disabled={activePane === PANE_TITLES.length}
            aria-label="Next pane"
          >
            ›
          </button>
        </div>
      </div>

      <div className="carousel__stage">
        {panes.map((pane, index) => {
          const number = index + 1;
          const hidden = number !== activePane;
          return (
            <section
              key={number}
              className="carousel__pane"
              data-pane={number}
              data-active={hidden ? undefined : 'true'}
              hidden={hidden}
              aria-labelledby={`pane-title-${number}`}
            >
              <header className="pane__head">
                <p className="pane__number">{String(number).padStart(2, '0')}</p>
                <h2 className="pane__title" id={`pane-title-${number}`}>
                  {PANE_TITLES[index]}
                </h2>
                <p className="pane__what">{PANE_WHATS[index]}</p>
              </header>
              {pane}
              <p className="method-note">
                Edition {meta.edition} · {METHOD_LABELS[filters.method]} normalization ·{' '}
                {block.countryCount} countries · {meta.leaves} indicators
              </p>
            </section>
          );
        })}
      </div>

      <div className="carousel__dots" role="group" aria-label="Choose a pane">
        {PANE_TITLES.map((title, index) => (
          <button
            key={title}
            type="button"
            className="carousel__dot"
            aria-label={`Go to pane ${index + 1}: ${title}`}
            aria-current={index + 1 === activePane ? 'true' : undefined}
            onClick={() => goTo(index + 1)}
          >
            <span className="sr-only">{index + 1}</span>
          </button>
        ))}
      </div>

      <details className="downloads">
        <summary>Download the data</summary>
        <ul>
          {payload.downloads.map((item) => (
            <li key={item.href}>
              <a href={item.href} download>
                {item.label}
              </a>
              <span className="micro hint"> — {item.note}</span>
            </li>
          ))}
        </ul>
        <p className="micro hint">
          One row per country. Column definitions: rank (1 = best), score (0–100),
          coverage (share of the index weight backed by a value), indicators present
          and total. Never compare scores across editions; use ranks.
        </p>
      </details>

      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </p>
    </div>
  );
}

function Disclosure({ table, label }: { table: TableModel; label: string }) {
  return (
    <details className="pane__table">
      <summary>{label}</summary>
      <PaneTable table={table} />
    </details>
  );
}
