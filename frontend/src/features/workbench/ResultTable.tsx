import type { ResultRow } from './types'
import { TagEditor } from './TagEditor'
import type { ResultColumn } from './viewPreferences'

interface ResultTableProps {
  rows: ResultRow[]
  allSelected: boolean
  onSelectAll: (selected: boolean) => void
  onSelectRow: (row: ResultRow, selected: boolean) => void
  onSaveDraft: (row: ResultRow, genres: string[], moods: string[]) => void
  visibleColumns: ResultColumn[]
}

const stateLabels = {
  new: 'Neu',
  current: 'Aktuell',
  changed: 'Verändert',
  written: 'Geschrieben',
  failed: 'Fehler',
}

export function ResultTable({
  rows,
  allSelected,
  onSelectAll,
  onSelectRow,
  onSaveDraft,
  visibleColumns,
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
            {visibleColumns.includes('artist') && <th>Interpret</th>}
            {visibleColumns.includes('title') && <th>Titel</th>}
            {visibleColumns.includes('file') && <th>Datei</th>}
            {visibleColumns.includes('genres') && <th>Genres</th>}
            {visibleColumns.includes('moods') && <th>Moods</th>}
            {visibleColumns.includes('status') && <th>Status</th>}
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
              {visibleColumns.includes('artist') && <td><span className="track-artist">{row.artist}</span></td>}
              {visibleColumns.includes('title') && <td><strong className="track-title">{row.title}</strong></td>}
              {visibleColumns.includes('file') && <td><code className="track-path">{row.relative_path}</code></td>}
              {visibleColumns.includes('genres') && <td>
                <TagEditor
                  kind="Genre"
                  values={row.draft.genres}
                  onChange={(genres) => onSaveDraft(row, genres, row.draft.moods)}
                />
              </td>}
              {visibleColumns.includes('moods') && <td>
                <TagEditor
                  kind="Mood"
                  values={row.draft.moods}
                  onChange={(moods) => onSaveDraft(row, row.draft.genres, moods)}
                />
              </td>}
              {visibleColumns.includes('status') && <td>
                <span className="draft-state" data-dirty={row.draft.dirty}>
                  {row.draft.dirty ? 'Bearbeitet' : 'Vorschlag'}
                </span>
                <span className="processing-state" data-state={row.processing_state}>
                  {stateLabels[row.processing_state]}
                </span>
              </td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
