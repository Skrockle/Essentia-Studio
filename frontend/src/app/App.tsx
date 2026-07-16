import { useState } from 'react'

import type { ViewId } from '../api/types'
import { AppNav } from '../components/AppNav'
import { AboutView } from '../features/settings/AboutView'
import { SettingsView } from '../features/settings/SettingsView'
import { WorkbenchView } from '../features/workbench/WorkbenchView'

const viewNames: Record<ViewId, string> = {
  workbench: 'Workbench',
  playlists: 'Playlists',
  jobs: 'Jobs & Verlauf',
  settings: 'Einstellungen',
  about: 'Über Essentia Studio',
}

function PlannedView({ view }: { view: 'playlists' | 'jobs' }) {
  const isPlaylist = view === 'playlists'
  return (
    <div className="view-stack narrow-view">
      <header className="view-heading">
        <div>
          <p className="eyebrow">{isPlaylist ? 'Navidrome' : 'Protokoll'}</p>
          <h1>{viewNames[view]}</h1>
          <p>
            {isPlaylist
              ? 'Preset-Browser, verschachtelte Regeln und .nsp-Verwaltung folgen im Playlist-Baustein.'
              : 'Laufende Analysen, Schreibvorgänge und Undo erscheinen hier mit ihrem Fortschritt.'}
          </p>
        </div>
      </header>
      <section className="panel planned-panel">
        <span>Nächster Baustein</span>
        <strong>{isPlaylist ? 'Smart-Playlist-Studio' : 'Persistente Job-Historie'}</strong>
      </section>
    </div>
  )
}

export function App() {
  const [activeView, setActiveView] = useState<ViewId>('workbench')

  return (
    <div className="app-shell">
      <AppNav activeView={activeView} onNavigate={setActiveView} />
      <main className="app-main" id="main-content">
        {activeView === 'workbench' && <WorkbenchView />}
        {activeView === 'playlists' && <PlannedView view="playlists" />}
        {activeView === 'jobs' && <PlannedView view="jobs" />}
        {activeView === 'settings' && <SettingsView />}
        {activeView === 'about' && <AboutView />}
      </main>
    </div>
  )
}
