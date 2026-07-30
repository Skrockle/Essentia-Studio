import type { LibraryTrack } from './types'
import type { LibraryColumn } from './viewPreferences'

interface LibraryTableProps {
  error: string | null
  isFilteredEmpty: boolean
  tracks: LibraryTrack[]
  selectedIds: ReadonlySet<number>
  onSelectAll: (selected: boolean) => void
  onSelectTrack: (trackId: number, selected: boolean) => void
  selectionDisabled: boolean
  visibleColumns: LibraryColumn[]
}

const stateLabels = {
  new: 'Neu',
  current: 'Aktuell',
  changed: 'Verändert',
  written: 'Geschrieben',
  failed: 'Fehler',
}

function libraryEmptyMessage(selectionDisabled: boolean, isFilteredEmpty: boolean): string {
  if (selectionDisabled) return 'Bibliothek wird geladen …'
  if (isFilteredEmpty) return 'Keine Titel für diesen Filter gefunden.'
  return 'Noch keine Titel gefunden. Starte zuerst einen Scan.'
}

function LibraryTableContent({
  error,
  isFilteredEmpty,
  tracks,
  selectedIds,
  onSelectAll,
  onSelectTrack,
  selectionDisabled,
  visibleColumns,
}: LibraryTableProps) {
  if (error) return <p className="notice notice--error">{error}</p>
  if (tracks.length === 0) {
    return <p className="library-panel__empty">{libraryEmptyMessage(selectionDisabled, isFilteredEmpty)}</p>
  }

  const allSelected = tracks.every((track) => selectedIds.has(track.id))
  return (
    <div className="library-table-scroll">
      <table className="library-table">
        <thead>
          <tr>
            <th>
              <input
                aria-label="Alle gescannten Titel analysieren"
                checked={allSelected}
                disabled={selectionDisabled}
                onChange={(event) => onSelectAll(event.target.checked)}
                type="checkbox"
              />
            </th>
            {visibleColumns.includes('artist') && <th>Interpret</th>}
            {visibleColumns.includes('title') && <th>Titel</th>}
            {visibleColumns.includes('file') && <th>Datei</th>}
            {visibleColumns.includes('album') && <th>Album</th>}
            {visibleColumns.includes('format') && <th>Format</th>}
            {visibleColumns.includes('status') && <th>Status</th>}
          </tr>
        </thead>
        <tbody>
          {tracks.map((track) => (
            <tr key={track.id}>
              <td>
                <input
                  aria-label={`${track.relative_path} analysieren`}
                  checked={selectedIds.has(track.id)}
                  disabled={selectionDisabled}
                  onChange={(event) => onSelectTrack(track.id, event.target.checked)}
                  type="checkbox"
                />
              </td>
              {visibleColumns.includes('artist') && <td className="track-artist">{track.artist}</td>}
              {visibleColumns.includes('title') && <td><strong className="track-title">{track.title}</strong></td>}
              {visibleColumns.includes('file') && <td><code className="track-path">{track.relative_path}</code></td>}
              {visibleColumns.includes('album') && <td className="track-album">{track.album ?? '—'}</td>}
              {visibleColumns.includes('format') && <td><span className="format-badge">{track.extension.slice(1).toUpperCase()}</span></td>}
              {visibleColumns.includes('status') && <td>
                <span className="processing-state" data-state={track.processing_state}>
                  {stateLabels[track.processing_state]}
                </span>
              </td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function LibraryTable(props: LibraryTableProps) {
  const { selectedIds, tracks } = props
  return (
    <section className="library-panel panel" aria-labelledby="library-heading">
      <div className="library-panel__header">
        <div>
          <p className="eyebrow">Gescannte Bibliothek</p>
          <h2 id="library-heading">Titel für die Analyse auswählen</h2>
        </div>
        <span><strong>{selectedIds.size}</strong> von {tracks.length} ausgewählt</span>
      </div>
      <LibraryTableContent {...props} />
    </section>
  )
}
