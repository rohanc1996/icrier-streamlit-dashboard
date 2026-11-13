import { methodShortLabel } from '../lib/scale';

interface RankingsToolbarProps {
  query: string;
  onQuery: (value: string) => void;
  visible: number;
  total: number;
  mode: 'rank' | 'score';
  onMode: (mode: 'rank' | 'score') => void;
  scale: string;
  scaleIds: string[];
  onScale: (scale: string) => void;
  showPillars: boolean;
  onShowPillars: (value: boolean) => void;
  caption: string;
}

export default function RankingsToolbar({
  query,
  onQuery,
  visible,
  total,
  mode,
  onMode,
  scale,
  scaleIds,
  onScale,
  showPillars,
  onShowPillars,
  caption,
}: RankingsToolbarProps) {
  return (
    <div className="panel toolbar">
      <div className="toolbar__row">
        <div className="field toolbar__filter">
          <label className="label" htmlFor="country-filter">
            Filter countries
          </label>
          <input
            id="country-filter"
            type="search"
            value={query}
            placeholder={`Filter ${total} countries…`}
            autoComplete="off"
            onChange={(event) => onQuery(event.target.value)}
          />
          <span className="micro hint">
            {visible} of {total} countries
          </span>
        </div>

        <div className="toolbar__controls">
          <fieldset className="toolbar__group">
            <legend className="toolbar__legend">Emphasis</legend>
            <div className="segmented">
              <label className="segmented__option">
                <input
                  type="radio"
                  name="emphasis"
                  value="rank"
                  checked={mode === 'rank'}
                  onChange={() => onMode('rank')}
                />
                <span>Rank</span>
              </label>
              <label className="segmented__option">
                <input
                  type="radio"
                  name="emphasis"
                  value="score"
                  checked={mode === 'score'}
                  onChange={() => onMode('score')}
                />
                <span>Score</span>
              </label>
            </div>
          </fieldset>

          <fieldset className="toolbar__group">
            <legend className="toolbar__legend">Scale</legend>
            <div className="segmented">
              {scaleIds.map((id) => (
                <label className="segmented__option" key={id}>
                  <input
                    type="radio"
                    name="scale"
                    value={id}
                    checked={scale === id}
                    onChange={() => onScale(id)}
                  />
                  <span>{methodShortLabel(id)}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="toolbar__checks">
            <label className="choice">
              <input
                type="checkbox"
                checked={showPillars}
                onChange={(event) => onShowPillars(event.target.checked)}
              />
              <span>Show pillars</span>
            </label>
            <label className="choice">
              <input
                type="checkbox"
                disabled
                aria-describedby="change-reason"
              />
              <span>Change vs 2025</span>
            </label>
          </div>
        </div>
      </div>

      <p id="change-reason" className="toolbar__reason">
        Change vs 2025 is not in this build: the 2025 comparison series is not
        connected to the table yet.
      </p>

      {/* IA §2: the scale control changes the numbers and, as the data shows,
          can change the league table. The caption is generated from the data. */}
      <p className="toolbar__caption">{caption}</p>
    </div>
  );
}
