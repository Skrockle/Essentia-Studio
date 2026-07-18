import { useEffect, useState } from 'react'

import type { ViewId } from '../api/types'
import { AppNav } from '../components/AppNav'
import { JobMonitorProvider } from '../features/jobs/useJobMonitor'
import { JobsView } from '../features/jobs/JobsView'
import { PlaylistsView } from '../features/playlists/PlaylistsView'
import { AboutView } from '../features/settings/AboutView'
import { SettingsView } from '../features/settings/SettingsView'
import { WorkbenchView } from '../features/workbench/WorkbenchView'
import {
  loadThemePreference,
  resolveTheme,
  saveThemePreference,
  type ThemePreference,
} from './theme'

export function App() {
  const [activeView, setActiveView] = useState<ViewId>('workbench')
  const [themePreference, setThemePreference] = useState(loadThemePreference)
  const [systemPrefersDark, setSystemPrefersDark] = useState(
    () => globalThis.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
  )

  useEffect(() => {
    const media = globalThis.matchMedia?.('(prefers-color-scheme: dark)')
    if (!media) return
    const update = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    const resolved = resolveTheme(themePreference, systemPrefersDark)
    document.documentElement.dataset.theme = resolved
    document.documentElement.style.colorScheme = resolved
    saveThemePreference(themePreference)
  }, [systemPrefersDark, themePreference])

  const changeTheme = (preference: ThemePreference) => setThemePreference(preference)

  return (
    <JobMonitorProvider>
      <div className="app-shell">
        <AppNav
          activeView={activeView}
          onNavigate={setActiveView}
          onThemeChange={changeTheme}
          themePreference={themePreference}
        />
        <main className="app-main" id="main-content">
          {activeView === 'workbench' && <WorkbenchView />}
          {activeView === 'playlists' && <PlaylistsView />}
          {activeView === 'jobs' && <JobsView />}
          {activeView === 'settings' && <SettingsView />}
          {activeView === 'about' && <AboutView />}
        </main>
      </div>
    </JobMonitorProvider>
  )
}
