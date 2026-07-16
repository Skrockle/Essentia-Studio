import type { ResultRow } from './types'
import { TagEditor } from './TagEditor'

interface ResultTableProps {
  rows: ResultRow[]
  allSelected: boolean
  onSelectAll: (selected: boolean) => void
  onSelectRow: (row: ResultRow, selected: boolean) => void
  onSaveDraft: (row: ResultRow, genres: string[], moods: string[]) => void
}

export function ResultTable({
  rows,
  allSelected,
  onSelectAll,
  onSelectRow,
  onSaveDraft,
}: ResultTableProps) {
  return (
    <div className="result-table-wrap panel">
      <table className="result-table">
        <thead>
          <tr>
            <th>
              <input
                aria-label="Alle gefilterten Titel auswählen"
                checked={allSelected}
                onChange={(event) => onSelectAll(event.target.checked)}
                type="checkbox"
              />
            </th>
            <th>Titel</th>
            <th>Genres</th>
            <th>Moods</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                <input
                  aria-label={`${row.relative_path} auswählen`}
                  checked={row.draft.selected}
                  onChange={(event) => onSelectRow(row, event.target.checked)}
                  type="checkbox"
                />
              </td>
              <td>
                <code className="track-path">{row.relative_path}</code>
              </td>
              <td>
                <TagEditor
                  kind="Genre"
                  values={row.draft.genres}
                  onChange={(genres) => onSaveDraft(row, genres, row.draft.moods)}
                />
              </td>
              <td>
                <TagEditor
                  kind="Mood"
                  values={row.draft.moods}
                  onChange={(moods) => onSaveDraft(row, row.draft.genres, moods)}
                />
              </td>
              <td>
                <span className="draft-state" data-dirty={row.draft.dirty}>
                  {row.draft.dirty ? 'Bearbeitet' : 'Vorschlag'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
