import { useCallback, useEffect, useState } from 'react'
import { ListMusic } from 'lucide-react'

import { apiRequest } from '../../api/client'
import { PlaylistManager } from './PlaylistManager'
import { PresetBrowser } from './PresetBrowser'
import { RuleBuilder } from './RuleBuilder'
import { ThisIsBuilder } from './ThisIsBuilder'
import type { PlaylistCatalog, PlaylistFile } from './types'

type Tab = 'presets' | 'this-is' | 'custom'

export function PlaylistsView() {
  const [catalog, setCatalog] = useState<PlaylistCatalog | null>(null)
  const [files, setFiles] = useState<PlaylistFile[]>([])
  const [tab, setTab] = useState<Tab>('presets')
  const [message, setMessage] = useState<string | null>(null)

  const loadFiles = useCallback(async () => setFiles(await apiRequest('/api/playlists')), [])

  useEffect(() => {
    void Promise.all([
      apiRequest<PlaylistCatalog>('/api/playlists/catalog'),
      apiRequest<PlaylistFile[]>('/api/playlists'),
    ]).then(([nextCatalog, nextFiles]) => {
      setCatalog(nextCatalog)
      setFiles(nextFiles)
    })
  }, [])

  function saved(file: PlaylistFile) {
    setMessage(`${file.name} gespeichert`)
    void loadFiles()
  }

  if (!catalog) return <section className="panel loading-panel">Playlist-Katalog wird geladen …</section>

  return (
    <div className="view-stack">
      <header className="view-heading"><div><p className="eyebrow">Navidrome Smart Playlists</p><h1>Playlist Studio</h1><p>298 Presets, 20 Künstler-Methoden und freie verschachtelte Regeln – direkt als .nsp in deinem Musik-Mount.</p></div><ListMusic className="section-icon" size={34} /></header>
      <div className="playlist-tabs" role="tablist"><button aria-selected={tab === 'presets'} onClick={() => setTab('presets')} role="tab" type="button">Presets</button><button aria-selected={tab === 'this-is'} onClick={() => setTab('this-is')} role="tab" type="button">This is …</button><button aria-selected={tab === 'custom'} onClick={() => setTab('custom')} role="tab" type="button">Eigene Regeln</button></div>
      {message && <p className="notice notice--success">{message}</p>}
      {tab === 'presets' && <PresetBrowser catalog={catalog} onSaved={saved} />}
      {tab === 'this-is' && <ThisIsBuilder catalog={catalog} onSaved={saved} />}
      {tab === 'custom' && <RuleBuilder catalog={catalog} onSaved={saved} />}
      <PlaylistManager files={files} onChanged={loadFiles} />
    </div>
  )
}
