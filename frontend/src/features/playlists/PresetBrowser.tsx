import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { PlaylistCatalog, PlaylistFile } from './types'

const PAGE_SIZE = 18

export function PresetBrowser({ catalog, onSaved }: { catalog: PlaylistCatalog; onSaved: (file: PlaylistFile) => void }) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const filtered = useMemo(
    () => catalog.presets.filter((preset) => `${preset.label} ${preset.category}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())),
    [catalog.presets, search],
  )
  const visible = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  async function create(slug: string, label: string) {
    const filename = `${slug}.nsp`
    onSaved(await apiRequest<PlaylistFile>(`/api/playlists/from-preset/${slug}`, { method: 'POST', body: JSON.stringify({ filename, overrides: { name: label } }) }))
  }

  return (
    <section className="playlist-section">
      <label className="search-field"><Search size={17} /><span className="sr-only">Presets filtern</span><input aria-label="Presets filtern" onChange={(event) => { setSearch(event.target.value); setPage(0) }} placeholder="298 Presets durchsuchen …" value={search} /></label>
      <div className="preset-grid">{visible.map((preset) => <article className="panel" key={preset.slug}><span>{preset.category}</span><strong>{preset.label}</strong><p>{String(preset.definition.comment ?? '')}</p><button onClick={() => create(preset.slug, preset.label)} type="button">Preset speichern</button></article>)}</div>
      <nav className="pager" aria-label="Preset-Seiten"><button disabled={page === 0} onClick={() => setPage((value) => value - 1)} type="button">Zurück</button><span>{page + 1} / {Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))}</span><button disabled={(page + 1) * PAGE_SIZE >= filtered.length} onClick={() => setPage((value) => value + 1)} type="button">Weiter</button></nav>
    </section>
  )
}
