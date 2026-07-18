import type { LibraryTrack } from './types'
import type { LibraryColumn } from './viewPreferences'

interface LibraryTableProps {
  tracks: LibraryTrack[]
  selectedIds: ReadonlySet<number>
  onSelectAll: (selected: boolean) => void
  onSelectTrack: (trackId: number, selected: boolean) => void
  visibleColumns: LibraryColumn[]
}

const stateLabels = {
  new: 'Neu',
  current: 'Aktuell',
  changed: 'Verändert',
  written: 'Geschrieben',
  failed: 'Fehler',
}

export function LibraryTable({
  tracks,
  selectedIds,
  onSelectAll,
  onSelectTrack,
  visibleColumns,
}: LibraryTableProps) {
  const allSelected = tracks.length > 0 && tracks.every((track) => selectedIds.has(track.id))

  return (
    <section className="library-panel panel" aria-labelledby="library-heading">
      <div className="library-panel__header">
        <div>
          <p className="eyebrow">Gescannte Bibliothek</p>
          <h2 id="library-heading">Titel für die Analyse auswählen</h2>
        </div>
        <span><strong>{selectedIds.size}</strong> von {tracks.length} ausgewählt</span>
      </div>
      {tracks.length === 0 ? (
        <p className="library-panel__empty">Noch keine Titel gefunden. Starte zuerst einen Scan.</p>
      ) : (
        <div className="library-table-scroll">
          <table className="library-table">
            <thead>
              <tr>
                <th>
                  <input
                    aria-label="Alle gescannten Titel analysieren"
                    checked={allSelected}
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
      )}
    </section>
  )
}
