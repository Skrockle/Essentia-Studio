import type { LibraryTrack } from './types'

interface LibraryTableProps {
  tracks: LibraryTrack[]
  selectedIds: ReadonlySet<number>
  onSelectAll: (selected: boolean) => void
  onSelectTrack: (trackId: number, selected: boolean) => void
}

export function LibraryTable({
  tracks,
  selectedIds,
  onSelectAll,
  onSelectTrack,
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
                <th>Titel</th>
                <th>Format</th>
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
                  <td><code className="track-path">{track.relative_path}</code></td>
                  <td><span className="format-badge">{track.extension.slice(1).toUpperCase()}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
