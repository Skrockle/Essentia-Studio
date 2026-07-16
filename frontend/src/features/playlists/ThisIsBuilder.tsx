import { useState } from 'react'

import { apiRequest } from '../../api/client'
import { PlaylistJson } from './RuleBuilder'
import type { PlaylistCatalog, PlaylistFile } from './types'

export function ThisIsBuilder({ catalog, onSaved }: { catalog: PlaylistCatalog; onSaved: (file: PlaylistFile) => void }) {
  const [artist, setArtist] = useState('')
  const [method, setMethod] = useState('greatest_hits')
  const [filename, setFilename] = useState('this-is.nsp')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)

  const payload = { filename, artist, method, limit: 50 }

  async function loadPreview() {
    setPreview(await apiRequest('/api/playlists/this-is/preview', { method: 'POST', body: JSON.stringify(payload) }))
  }

  async function save() {
    onSaved(await apiRequest<PlaylistFile>('/api/playlists/this-is', { method: 'POST', body: JSON.stringify(payload) }))
  }

  return (
    <div className="playlist-editor-grid">
      <section className="playlist-form panel">
        <div className="form-grid"><label>Album-Künstler<input onChange={(event) => setArtist(event.target.value)} value={artist} /></label><label>Methode<select onChange={(event) => setMethod(event.target.value)} value={method}>{catalog.this_is_methods.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>Dateiname<input onChange={(event) => setFilename(event.target.value)} value={filename} /></label></div>
        <div className="button-row"><button onClick={loadPreview} type="button">Vorschau erzeugen</button><button className="primary-button" disabled={!preview} onClick={save} type="button">Playlist speichern</button></div>
      </section>
      {preview ? <PlaylistJson definition={preview} /> : <div className="playlist-placeholder panel">Vorschau erzeugen, prüfen, dann speichern.</div>}
    </div>
  )
}
