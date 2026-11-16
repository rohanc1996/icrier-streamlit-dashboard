import type { PaneTableModel } from '../../lib/overview-types';

/**
 * The table fallback carries the same numbers as the chart beside it, so the
 * chart is never the only route to the data. Rows arrive pre-formatted from
 * the build; nothing here rounds a figure.
 */
export default function PaneTable({ table }: { table: PaneTableModel }) {
  const numeric = new Set(
    table.numericColumns ?? [0, table.columns.length - 1],
  );
  const isNumeric = (index: number) => numeric.has(index);

  return (
    <div className="table-wrap pane-table">
      <table>
        <caption className="sr-only">{table.caption}</caption>
        <thead>
          <tr>
            {table.columns.map((column, index) => (
              <th
                key={column}
                scope="col"
                className={isNumeric(index) ? 'num' : undefined}
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row.join('|')}>
              {row.map((cell, index) => (
                <td
                  key={`${index}-${cell}`}
                  className={`${isNumeric(index) ? 'num' : ''}${
                    index === 0 ? ' rank-cell' : ''
                  }`.trim() || undefined}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="table-note">{table.note}</p>
    </div>
  );
}
