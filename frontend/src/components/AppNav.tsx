import {
  AudioLines,
  CircleHelp,
  History,
  ListMusic,
  Settings,
  type LucideIcon,
} from 'lucide-react'

import type { ViewId } from '../api/types'

interface AppNavProps {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
}

const navigation: Array<{ id: ViewId; label: string; icon: LucideIcon }> = [
  { id: 'workbench', label: 'Workbench', icon: AudioLines },
  { id: 'playlists', label: 'Playlists', icon: ListMusic },
  { id: 'jobs', label: 'Jobs & Verlauf', icon: History },
  { id: 'settings', label: 'Einstellungen', icon: Settings },
  { id: 'about', label: 'Über Essentia Studio', icon: CircleHelp },
]

export function AppNav({ activeView, onNavigate }: AppNavProps) {
  return (
    <nav className="app-nav" aria-label="Hauptnavigation">
      <div className="app-nav__identity">
        <span className="app-nav__mark" aria-hidden="true">
          ES
        </span>
        <span>
          <strong>Essentia</strong>
          <small>Studio</small>
        </span>
      </div>

      <div className="app-nav__items">
        {navigation.map(({ id, label, icon: Icon }) => (
          <button
            aria-label={label}
            className="app-nav__button"
            data-active={activeView === id}
            key={id}
            onClick={() => onNavigate(id)}
            type="button"
          >
            <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <p className="app-nav__scope">
        <span className="status-dot" aria-hidden="true" />
        Lokales Netzwerk
      </p>
    </nav>
  )
}
