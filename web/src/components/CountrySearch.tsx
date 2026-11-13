import { useId, useMemo, useState, type FormEvent } from 'react';
import { plural } from '../lib/format';
import { readScaleParam, withScale } from '../lib/scale';

interface CountrySearchProps {
  countries: Array<{ iso3: string; name: string; fullName: string }>;
  scaleIds: string[];
  defaultScale: string;
}

/**
 * Keyboard-operable header search stub. Enter opens the first match; the
 * result links are ordinary anchors, so Tab and Shift+Tab work. The live
 * region announces how many countries match.
 *
 * TODO (later wave): the full CountrySearch splits "open the first result"
 * from "filter the table with the rest", and closes on outside click.
 */
export default function CountrySearch({ countries, scaleIds, defaultScale }: CountrySearchProps) {
  const [query, setQuery] = useState('');
  const inputId = useId();
  const statusId = useId();
  const listId = useId();

  const trimmed = query.trim().toLowerCase();
  const matches = useMemo(() => {
    if (trimmed.length === 0) return [];
    return countries
      .filter((country) => {
        return (
          country.name.toLowerCase().includes(trimmed) ||
          country.fullName.toLowerCase().includes(trimmed) ||
          country.iso3.toLowerCase().includes(trimmed)
        );
      })
      .slice(0, 6);
  }, [countries, trimmed]);

  const status =
    trimmed.length === 0
      ? ''
      : matches.length === 0
        ? `No countries match “${query.trim()}”.`
        : `${matches.length} ${plural(matches.length, 'country', 'countries')} match. Press Enter to open ${matches[0].name}, or Tab to the results.`;

  function hrefFor(iso3: string): string {
    if (typeof window === 'undefined') return `/country/${iso3}`;
    const scale = readScaleParam(window.location.search, scaleIds, defaultScale);
    return withScale(`/country/${iso3}`, scale, defaultScale);
  }

  function openFirst(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (matches.length > 0) window.location.href = hrefFor(matches[0].iso3);
  }

  return (
    <form className="country-search" role="search" onSubmit={openFirst}>
      <label className="sr-only" htmlFor={inputId}>
        Search countries
      </label>
      <input
        id={inputId}
        type="search"
        value={query}
        placeholder="Search countries…"
        autoComplete="off"
        aria-describedby={statusId}
        aria-controls={listId}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setQuery('');
        }}
      />
      <p id={statusId} className="sr-only" aria-live="polite" aria-atomic="true">
        {status}
      </p>
      <ul id={listId} className="country-search__results" hidden={matches.length === 0}>
        {matches.map((country) => (
          <li key={country.iso3}>
            <a href={hrefFor(country.iso3)}>
              <span>{country.name}</span>
              <span className="country-search__iso">{country.iso3}</span>
            </a>
          </li>
        ))}
      </ul>
    </form>
  );
}
