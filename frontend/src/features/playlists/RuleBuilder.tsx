import { useMemo, useState } from 'react'

import { apiRequest } from '../../api/client'
import { RuleGroup } from './RuleGroup'
import { group, serializeGroup } from './rules'
import type { PlaylistCatalog, PlaylistFile } from './types'

export function RuleBuilder({ catalog, onSaved }: { catalog: PlaylistCatalog; onSaved: (file: PlaylistFile) => void }) {
  const [name, setName] = useState('Meine Smart Playlist')
  const [filename, setFilename] = useState('meine-playlist.nsp')
  const [limit, setLimit] = useState(100)
  const [rules, setRules] = useState(() => group())
  const definition = useMemo(() => ({ name, ...serializeGroup(rules), limit }), [limit, name, rules])

  async function save() {
    onSaved(await apiRequest<PlaylistFile>('/api/playlists', { method: 'POST', body: JSON.stringify({ filename, definition }) }))
  }

  return (
    <div className="playlist-editor-grid">
      <div className="playlist-form panel">
        <div className="form-grid"><label>Name<input onChange={(event) => setName(event.target.value)} value={name} /></label><label>Dateiname<input onChange={(event) => setFilename(event.target.value)} value={filename} /></label><label>Limit<input max={100000} min={1} onChange={(event) => setLimit(Number(event.target.value))} type="number" value={limit} /></label></div>
        <RuleGroup catalog={catalog} node={rules} onChange={setRules} root={rules} />
        <button className="primary-button" onClick={save} type="button">Playlist speichern</button>
      </div>
      <PlaylistJson definition={definition} />
    </div>
  )
}

export function PlaylistJson({ definition }: { definition: Record<string, unknown> }) {
  return <pre className="playlist-json panel">{JSON.stringify(definition, null, 2)}</pre>
}
