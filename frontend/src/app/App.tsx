import { useState } from 'react'

import type { ViewId } from '../api/types'
import { AppNav } from '../components/AppNav'
import { JobMonitorProvider } from '../features/jobs/useJobMonitor'
import { JobsView } from '../features/jobs/JobsView'
import { PlaylistsView } from '../features/playlists/PlaylistsView'
import { AboutView } from '../features/settings/AboutView'
import { SettingsView } from '../features/settings/SettingsView'
import { WorkbenchView } from '../features/workbench/WorkbenchView'

export function App() {
  const [activeView, setActiveView] = useState<ViewId>('workbench')

  return (
    <JobMonitorProvider>
      <div className="app-shell">
        <AppNav activeView={activeView} onNavigate={setActiveView} />
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
