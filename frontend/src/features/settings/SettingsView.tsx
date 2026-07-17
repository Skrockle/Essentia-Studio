import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Cpu, Database, FolderOpen, Save } from 'lucide-react'

import { ApiError, apiRequest } from '../../api/client'
import type {
  AppSettings,
  AutomationStatus,
  Capabilities,
  EffectiveSettings,
  PathCapability,
} from '../../api/types'
import { AutomationSettings } from './AutomationSettings'
import { SettingField } from './SettingField'

const statusLabels = { ready: 'Bereit', read_only: 'Nur lesen', missing: 'Fehlt' }

interface PathStatusProps {
  icon: typeof FolderOpen
  label: string
  capability: PathCapability
}

function PathStatus({ icon: Icon, label, capability }: PathStatusProps) {
  return (
    <article className="path-status">
      <Icon aria-hidden="true" size={19} />
      <div><span>{label}</span><code>{capability.path}</code></div>
      <span className="status-label" data-status={capability.status}>{statusLabels[capability.status]}</span>
    </article>
  )
}

function changedSettings(
  original: AppSettings,
  draft: AppSettings,
  sources: EffectiveSettings['sources'],
): Record<string, Record<string, unknown>> {
  const patch: Record<string, Record<string, unknown>> = {}
  for (const section of Object.keys(draft) as Array<keyof AppSettings>) {
    for (const key of Object.keys(draft[section])) {
      const path = `${section}.${key}`
      const originalValue = (original[section] as unknown as Record<string, unknown>)[key]
      const draftValue = (draft[section] as unknown as Record<string, unknown>)[key]
      if (draftValue !== originalValue && sources[path] !== 'env') {
        patch[section] ??= {}
        patch[section][key] = draftValue
      }
    }
  }
  return patch
}

export function SettingsView() {
  const [effective, setEffective] = useState<EffectiveSettings | null>(null)
  const [draft, setDraft] = useState<AppSettings | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [automationStatus, setAutomationStatus] = useState<AutomationStatus | null>(null)
  const [writeConfirmed, setWriteConfirmed] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<EffectiveSettings>('/api/settings'),
      apiRequest<Capabilities>('/api/capabilities'),
      apiRequest<AutomationStatus>('/api/automation/status'),
    ])
      .then(([loadedSettings, loadedCapabilities, loadedStatus]) => {
        if (!active) return
        setEffective(loadedSettings)
        setDraft(loadedSettings.values)
        setCapabilities(loadedCapabilities)
        setAutomationStatus(loadedStatus)
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : 'Einstellungen fehlen.')
      })
    return () => { active = false }
  }, [])

  async function saveSettings() {
    if (!effective || !draft) return
    setMessage('')
    if (
      draft.automation.mode === 'analyze_and_write' &&
      effective.sources['automation.mode'] !== 'env' &&
      !writeConfirmed
    ) {
      setMessage('Bitte bestätige das automatische Schreiben ausdrücklich.')
      return
    }
    try {
      const patch = changedSettings(effective.values, draft, effective.sources)
      const saved = await apiRequest<EffectiveSettings>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(patch),
      })
      setEffective(saved)
      setDraft(saved.values)
      setWriteConfirmed(false)
      setAutomationStatus(await apiRequest<AutomationStatus>('/api/automation/status'))
      setMessage('Änderungen gespeichert.')
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Speichern fehlgeschlagen.')
    }
  }

  if (!effective || !draft || !capabilities || !automationStatus) {
    return <div className="panel loading-panel">Einstellungen werden geladen …</div>
  }
  const sources = effective.sources
  const analysis = draft.analysis
  const isCudaImage = capabilities.image_variant === 'cuda'
  const updateAnalysis = (patch: Partial<AppSettings['analysis']>) =>
    setDraft({ ...draft, analysis: { ...analysis, ...patch } })

  return (
    <div className="view-stack">
      <header className="view-heading">
        <div>
          <p className="eyebrow">System, Analyse & Automatik</p>
          <h1>Einstellungen</h1>
          <p>Rechenleistung abstimmen und neue Musik kontrolliert verarbeiten.</p>
        </div>
        <button className="primary-button" onClick={saveSettings} type="button">
          <Save aria-hidden="true" size={17} /> Änderungen speichern
        </button>
      </header>
      {message && <p className="notice">{message}</p>}

      <section className="panel settings-section" aria-labelledby="storage-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Speicherorte</p><h2 id="storage-heading">Eingebundene Verzeichnisse</h2></div>
          <span className="section-note">Container-Pfade</span>
        </div>
        <div className="path-grid">
          <PathStatus icon={FolderOpen} label="Mediathek" capability={capabilities.music_root} />
          <PathStatus icon={Database} label="Anwendungsdaten" capability={capabilities.data_dir} />
          <PathStatus icon={FolderOpen} label="Smart Playlists" capability={capabilities.playlist_dir} />
        </div>
      </section>

      <div className="settings-columns">
        <section className="panel settings-section" aria-labelledby="compute-heading">
          <div className="section-heading">
            <div><p className="eyebrow">Rechenart</p><h2 id="compute-heading">{isCudaImage ? 'CUDA-Image' : 'CPU-Image'}</h2></div>
            <Cpu aria-hidden="true" className="section-icon" size={23} />
          </div>
          <p className="section-copy">
            {isCudaImage ? 'Dieses Image kann CPU oder eine erkannte NVIDIA-GPU verwenden.' : 'Dieses Image analysiert lokal auf der CPU. Für NVIDIA-GPUs ist das CUDA-Image nötig.'}
          </p>
          <SettingField id="compute-preference" label="Bevorzugte Rechenart" source={sources['analysis.compute']}>
            <select id="compute-preference" value={analysis.compute} disabled={sources['analysis.compute'] === 'env'} onChange={(event) => updateAnalysis({ compute: event.target.value as AppSettings['analysis']['compute'] })}>
              <option value="auto">Automatisch</option><option value="cpu">CPU</option>
              <option value="cuda" disabled={!capabilities.available_compute.includes('cuda')}>NVIDIA CUDA</option>
            </select>
          </SettingField>
          <div className="model-status">
            {capabilities.models.length ? <Check size={17} /> : <AlertTriangle size={17} />}
            <span><strong>Geladene Modelle</strong>{capabilities.models.length ? capabilities.models.map((model) => model.name).join(', ') : 'Werden mit dem Analysemodul erkannt.'}</span>
          </div>
        </section>

        <section className="panel settings-section" aria-labelledby="analysis-heading">
          <div className="section-heading"><div><p className="eyebrow">Standardwerte</p><h2 id="analysis-heading">Analyse</h2></div></div>
          <div className="form-grid">
            <SettingField id="analysis-workers" label="Worker" source={sources['analysis.workers']}>
              <input id="analysis-workers" aria-label="Worker" min="1" max="64" type="number" value={analysis.workers} disabled={sources['analysis.workers'] === 'env'} onChange={(event) => updateAnalysis({ workers: Number(event.target.value) })} />
            </SettingField>
            <SettingField id="max-audio-seconds" label="Maximale Audiolänge" source={sources['analysis.max_audio_seconds']}>
              <span className="input-with-unit"><input id="max-audio-seconds" min="1" max="3600" type="number" value={analysis.max_audio_seconds} disabled={sources['analysis.max_audio_seconds'] === 'env'} onChange={(event) => updateAnalysis({ max_audio_seconds: Number(event.target.value) })} /><span>Sek.</span></span>
            </SettingField>
            <SettingField id="genre-count" label="Anzahl Genres" source={sources['analysis.genre_count']}>
              <input id="genre-count" min="1" max="20" type="number" value={analysis.genre_count} disabled={sources['analysis.genre_count'] === 'env'} onChange={(event) => updateAnalysis({ genre_count: Number(event.target.value) })} />
            </SettingField>
            <SettingField id="genre-threshold" label="Genre-Schwelle" source={sources['analysis.genre_threshold']}>
              <input id="genre-threshold" min="0" max="1" step="0.001" type="number" value={analysis.genre_threshold} disabled={sources['analysis.genre_threshold'] === 'env'} onChange={(event) => updateAnalysis({ genre_threshold: Number(event.target.value) })} />
            </SettingField>
            <SettingField id="mood-threshold" label="Mood-Schwelle" source={sources['analysis.mood_threshold']}>
              <input id="mood-threshold" min="0" max="1" step="0.001" type="number" value={analysis.mood_threshold} disabled={sources['analysis.mood_threshold'] === 'env'} onChange={(event) => updateAnalysis({ mood_threshold: Number(event.target.value) })} />
            </SettingField>
          </div>
          <label className="check-row"><input type="checkbox" checked={analysis.write_confidence_tags} disabled={sources['analysis.write_confidence_tags'] === 'env'} onChange={(event) => updateAnalysis({ write_confidence_tags: event.target.checked })} />Konfidenzwerte in verwaltete Tags schreiben</label>
          <label className="check-row"><input type="checkbox" checked={analysis.overwrite_existing} disabled={sources['analysis.overwrite_existing'] === 'env'} onChange={(event) => updateAnalysis({ overwrite_existing: event.target.checked })} />Bestehende verwaltete Tags standardmäßig ersetzen</label>
        </section>
      </div>

      <AutomationSettings
        value={draft.automation}
        sources={sources}
        status={automationStatus}
        writeConfirmed={writeConfirmed}
        onWriteConfirmedChange={setWriteConfirmed}
        onChange={(automation) => setDraft({ ...draft, automation })}
      />
    </div>
  )
}
