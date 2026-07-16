import { useState } from 'react'
import { ArrowRight, AudioWaveform, FolderSearch, Sparkles } from 'lucide-react'

import type { ViewId } from '../api/types'
import { AppNav } from '../components/AppNav'
import { AboutView } from '../features/settings/AboutView'
import { SettingsView } from '../features/settings/SettingsView'

const viewNames: Record<ViewId, string> = {
  workbench: 'Workbench',
  playlists: 'Playlists',
  jobs: 'Jobs & Verlauf',
  settings: 'Einstellungen',
  about: 'Über Essentia Studio',
}

function WorkbenchView() {
  return (
    <div className="view-stack">
      <header className="workbench-hero">
        <div>
          <p className="eyebrow">Mediathek-Analyse</p>
          <h1>Aus Klang wird Ordnung.</h1>
          <p>
            Scanne deine eingebundene Mediathek, analysiere Genres und Moods und prüfe jede
            Änderung, bevor sie geschrieben wird.
          </p>
        </div>
        <div className="signal-wave" aria-hidden="true">
          {[14, 28, 19, 42, 31, 55, 24, 47, 63, 34, 51, 25, 39, 18, 31, 13].map(
            (height, index) => (
              <span key={index} style={{ height }} />
            ),
          )}
        </div>
      </header>

      <section className="panel workbench-empty">
        <div className="empty-icon">
          <AudioWaveform aria-hidden="true" size={30} />
        </div>
        <div>
          <p className="eyebrow">Bereit für den ersten Scan</p>
          <h2>Noch keine Titel im Workbench</h2>
          <p>
            Der Bibliotheksscan und die Analysewarteschlange werden im nächsten Baustein aktiviert.
            Bis dahin kannst du unter Einstellungen Mounts und CPU-/CUDA-Status prüfen.
          </p>
        </div>
        <button className="primary-button" disabled type="button">
          Mediathek scannen <ArrowRight aria-hidden="true" size={17} />
        </button>
      </section>

      <div className="workflow-grid" aria-label="Geplanter Analyseablauf">
        <article>
          <FolderSearch aria-hidden="true" size={20} />
          <span>01 · Finden</span>
          <strong>Titel sicher unter /music erfassen</strong>
        </article>
        <article className="genre-card">
          <Sparkles aria-hidden="true" size={20} />
          <span>02 · Genre</span>
          <strong>Vorschläge prüfen und frei ergänzen</strong>
          <div className="chip-row">
            <span>Electronic</span>
            <span>Ambient</span>
          </div>
        </article>
        <article className="mood-card">
          <AudioWaveform aria-hidden="true" size={20} />
          <span>03 · Mood</span>
          <strong>Stimmung anpassen und auswählen</strong>
          <div className="chip-row">
            <span>Dreamy</span>
            <span>Calm</span>
          </div>
        </article>
      </div>
    </div>
  )
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
