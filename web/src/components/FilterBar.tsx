import { useEffect, useState } from 'react';
import {
  ALL_COUNTRIES,
  BASIS_LABELS,
  BASIS_ORDER,
  GROUP_IDS,
  GROUP_LABELS,
  METHOD_LABELS,
  METHODS,
  SHOW_NORMALIZATION_CONTROL,
  YEARS,
  meta,
  type Filters,
  type GroupId,
} from '../lib/site';

interface FilterBarProps {
  filters: Filters;
  onChange: (next: Filters) => void;
  onReset: () => void;
  /** Sentence naming the active view. */
  summary: string;
}

/** One control group with an instruction label, not a bare field name. */
function ControlGroup({
  legend,
  hint,
  children,
}: {
  legend: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="filterbar__group">
      <legend className="filterbar__legend">{legend}</legend>
      {children}
      {hint && <p className="filterbar__hint">{hint}</p>}
    </fieldset>
  );
}

export default function FilterBar({ filters, onChange, onReset, summary }: FilterBarProps) {
  const [open, setOpen] = useState(false);
  const [compact, setCompact] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 900px)');
    const apply = () => setCompact(query.matches);
    apply();
    query.addEventListener('change', apply);
    return () => query.removeEventListener('change', apply);
  }, []);

  const availableBasis = meta.basisAvailability[filters.year] ?? ['absolute'];
  function set(patch: Partial<Filters>) {
    onChange({ ...filters, ...patch });
  }

  function toggleYear(year: string) {
    const has = filters.years.includes(year);
    const next = has
      ? filters.years.filter((value) => value !== year)
      : [...filters.years, year].sort();
    if (next.length === 0) return;
    const latest = next[next.length - 1];
    const available = meta.basisAvailability[latest] ?? ['absolute'];
    set({
      years: next,
      year: latest,
      basis: available.includes(filters.basis) ? filters.basis : available[0],
    });
  }

  const body = (
    <div className="filterbar__grid">
      <ControlGroup legend="Score basis">
        <div className="segmented segmented--wrap">
          {BASIS_ORDER.map((basis) => {
            const disabled = !availableBasis.includes(basis);
            return (
              <label
                className="segmented__option"
                key={basis}
                title={disabled ? `No ${basis} dataset for ${filters.year}` : undefined}
              >
                <input
                  type="radio"
                  name="score-basis"
                  value={basis}
                  checked={filters.basis === basis}
                  disabled={disabled}
                  onChange={() => set({ basis })}
                />
                <span>{BASIS_LABELS[basis]}</span>
              </label>
            );
          })}
        </div>
        {availableBasis.length < BASIS_ORDER.length && (
          <p className="filterbar__hint">
            Relative and combined exist for 2026 only — earlier editions published
            absolute values.
          </p>
        )}
      </ControlGroup>

      <ControlGroup legend="Select year" hint="Several years open the rank tracker.">
        <div className="segmented segmented--wrap">
          {YEARS.map((year) => (
            <label className="segmented__option" key={year}>
              <input
                type="checkbox"
                name="year"
                value={year}
                checked={filters.years.includes(year)}
                onChange={() => toggleYear(year)}
              />
              <span>{year}</span>
            </label>
          ))}
        </div>
      </ControlGroup>

      <ControlGroup legend="Select country grouping">
        <div className="filterbar__stack">
          <select
            aria-label="Select country grouping"
            value={filters.group}
            onChange={(event) => set({ group: event.target.value as GroupId })}
          >
            {GROUP_IDS.map((id) => (
              <option value={id} key={id}>
                {GROUP_LABELS[id]}
              </option>
            ))}
          </select>

          {filters.group === 'custom' && (
            <select
              className="filterbar__multi"
              aria-label="Select countries for the custom grouping"
              multiple
              size={6}
              value={filters.custom}
              onChange={(event) =>
                set({
                  custom: Array.from(event.target.selectedOptions, (option) => option.value),
                })
              }
            >
              {ALL_COUNTRIES.map((country) => (
                <option value={country.iso3} key={country.iso3}>
                  {country.name}
                </option>
              ))}
            </select>
          )}

          <div className="filterbar__compare">
            <span className="filterbar__sublabel">Compare two countries</span>
            <div className="filterbar__pair">
              {[0, 1].map((slot) => (
                <select
                  key={slot}
                  aria-label={slot === 0 ? 'First country to compare' : 'Second country to compare'}
                  value={filters.compare[slot] ?? ''}
                  onChange={(event) => {
                    const next = [...filters.compare];
                    next[slot] = event.target.value;
                    set({ compare: next.filter(Boolean) as string[] });
                  }}
                >
                  <option value="">—</option>
                  {ALL_COUNTRIES.map((country) => (
                    <option value={country.iso3} key={country.iso3}>
                      {country.name}
                    </option>
                  ))}
                </select>
              ))}
            </div>
          </div>
        </div>
      </ControlGroup>

      {SHOW_NORMALIZATION_CONTROL && (
        <ControlGroup legend="Normalization method">
          <div className="segmented">
            {METHODS.map((id) => (
              <label className="segmented__option" key={id}>
                <input
                  type="radio"
                  name="normalization"
                  value={id}
                  checked={filters.method === id}
                  onChange={() => set({ method: id })}
                />
                <span>{METHOD_LABELS[id]}</span>
              </label>
            ))}
          </div>
          <p className="filterbar__hint">
            Provisional control: whether public readers see this is still open.
          </p>
        </ControlGroup>
      )}

      {!SHOW_NORMALIZATION_CONTROL && (
        <details className="filterbar__advanced">
          <summary>Advanced / methodology</summary>
          <ControlGroup legend="Normalization method">
            <div className="segmented">
              {METHODS.map((id) => (
                <label className="segmented__option" key={id}>
                  <input
                    type="radio"
                    name="normalization"
                    value={id}
                    checked={filters.method === id}
                    onChange={() => set({ method: id })}
                  />
                  <span>{METHOD_LABELS[id]}</span>
                </label>
              ))}
            </div>
            <p className="filterbar__hint">
              Provisional: whether public readers see this control is an open question.
              The default is stated in the active-view line above.
            </p>
          </ControlGroup>
        </details>
      )}
    </div>
  );

  const active = (
    <div className="filterbar__active">
      <p className="filterbar__selection" aria-live="polite">
        <span className="filterbar__selection-label">Showing</span> {summary}
      </p>
      <button type="button" className="filterbar__reset" onClick={onReset}>
        Reset view
      </button>
    </div>
  );

  if (compact) {
    return (
      <details
        className="filterbar filterbar--compact"
        open={open}
        onToggle={(event) => setOpen((event.target as HTMLDetailsElement).open)}
      >
        <summary>
          Filters
          <span className="filterbar__summary-text"> — {summary}</span>
        </summary>
        {active}
        {body}
      </details>
    );
  }

  return (
    <section className="filterbar" aria-label="View filters">
      {active}
      {body}
    </section>
  );
}
