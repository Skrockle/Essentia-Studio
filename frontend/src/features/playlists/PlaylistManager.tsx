import { useState } from 'react'
import { AlertTriangle, FileMusic, Trash2 } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { PlaylistFile } from './types'

export function PlaylistManager({ files, onChanged }: { files: PlaylistFile[]; onChanged: () => void }) {
  const [confirming, setConfirming] = useState<PlaylistFile | null>(null)

  async function remove(file: PlaylistFile) {
    await apiRequest(`/api/playlists/${encodeURIComponent(file.name)}`, { method: 'DELETE', body: JSON.stringify({ expected_fingerprint: file.fingerprint }) })
    setConfirming(null)
    onChanged()
  }

  return (
    <section className="panel playlist-manager">
      <div className="section-heading"><h2>Dateien im Mount</h2><FileMusic size={19} /></div>
      {files.length === 0 ? <p className="section-copy">Noch keine .nsp-Dateien.</p> : <div className="playlist-files">{files.map((file) => <article key={file.name}>{file.status === 'valid' ? <FileMusic size={17} /> : <AlertTriangle size={17} />}<div><strong>{file.name}</strong><span>{file.definition?.name ? String(file.definition.name) : file.error}</span></div><button aria-label={`${file.name} löschen`} disabled={file.status !== 'valid'} onClick={() => setConfirming(file)} type="button"><Trash2 size={15} /> Playlist löschen</button></article>)}</div>}
      {confirming && <div className="delete-confirm"><p><strong>{confirming.name}</strong> wirklich löschen?</p><button onClick={() => setConfirming(null)} type="button">Abbrechen</button><button onClick={() => remove(confirming)} type="button">Löschen bestätigen</button></div>}
    </section>
  )
}
