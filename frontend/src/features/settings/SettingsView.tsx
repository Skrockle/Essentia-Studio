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
import { BenchmarkPanel } from './BenchmarkPanel'
import { SettingField } from './SettingField'
import { presentModels } from './modelPresentation'
import { percentageToThreshold, thresholdToPercentage } from './percentageThreshold'

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

function ModelStatus({ models }: Pick<Capabilities, 'models'>) {
  const presentedModels = presentModels(models)
  return (
    <div className="model-status">
      {models.length ? <Check size={17} /> : <AlertTriangle size={17} />}
      <span>
        <strong>Aktive Analysemodelle</strong>
        {presentedModels.length ? presentedModels.join(' · ') : 'Werden mit dem Analysemodul erkannt.'}
        {models.length > 0 && (
          <details className="model-details">
            <summary>Technische Modelldetails</summary>
            <code>{models.map((model) => model.name).join('\n')}</code>
          </details>
        )}
      </span>
    </div>
  )
}

interface CudaTuningProps {
  analysis: AppSettings['analysis']
  sources: EffectiveSettings['sources']
  onChange: (patch: Partial<AppSettings['analysis']>) => void
  enabled: boolean
}

function CudaTuning({ analysis, sources, onChange, enabled }: CudaTuningProps) {
  if (!enabled) return null
  return (
    <div className="cuda-tuning" aria-labelledby="cuda-tuning-heading">
      <div className="cuda-tuning__heading">
        <div><p className="eyebrow">NVIDIA CUDA</p><h3 id="cuda-tuning-heading">GPU-Tuning</h3></div>
        <span className="cuda-tuning__badge">1 GPU-Worker</span>
      </div>
      <p className="section-copy">Die GPU bleibt als einzelner Worker reserviert. Batchgröße und Warteschlange bestimmen, wie viel Arbeit gleichzeitig im Grafikspeicher liegt.</p>
      <div className="form-grid cuda-tuning__grid">
        <SettingField id="gpu-workers" label="GPU-Worker" explanation="Die GPU-Pipeline läuft bewusst mit genau einem Worker, damit der Grafikspeicher stabil und vorhersehbar genutzt wird." source={sources['analysis.gpu_workers']}>
          <input id="gpu-workers" aria-label="GPU-Worker" min="1" max="1" type="number" value={analysis.gpu_workers} disabled />
        </SettingField>
        <SettingField id="gpu-batch-size" label="GPU-Batchgröße" explanation="Mehrere Titel werden gemeinsam an die GPU übergeben. Erhöhe den Wert nur, wenn ausreichend VRAM frei ist." source={sources['analysis.gpu_batch_size']}>
          <select id="gpu-batch-size" value={analysis.gpu_batch_size} disabled={sources['analysis.gpu_batch_size'] === 'env'} onChange={(event) => onChange({ gpu_batch_size: Number(event.target.value) as AppSettings['analysis']['gpu_batch_size'] })}>
            {[1, 2, 4, 8].map((size) => <option key={size} value={size}>{size} Titel</option>)}
          </select>
        </SettingField>
        <SettingField id="gpu-queue-size" label="CUDA-Queue" explanation="Anzahl der Titel, die auf die GPU warten dürfen. 8 ist der sichere Standard für das Dev-Image." source={sources['analysis.gpu_queue_size']}>
          <input id="gpu-queue-size" aria-label="CUDA-Queue" min="1" max="256" type="number" value={analysis.gpu_queue_size} disabled={sources['analysis.gpu_queue_size'] === 'env'} onChange={(event) => onChange({ gpu_queue_size: Number(event.target.value) })} />
        </SettingField>
      </div>
    </div>
  )
}

interface CpuWorkerFieldProps {
  analysis: AppSettings['analysis']
  sources: EffectiveSettings['sources']
  onChange: (patch: Partial<AppSettings['analysis']>) => void
}

function CpuWorkerField({ analysis, sources, onChange }: CpuWorkerFieldProps) {
  const lockedByEnvironment = sources['analysis.cpu_workers'] === 'env' || sources['analysis.workers'] === 'env'
  const source = lockedByEnvironment ? 'env' : sources['analysis.cpu_workers']
  const value = analysis.cpu_workers === 1 ? analysis.workers : analysis.cpu_workers
  return (
    <SettingField id="analysis-workers" label="CPU-Worker" explanation="Anzahl der Titel, die parallel auf der CPU analysiert werden. Mehr Worker benötigen entsprechend mehr Arbeitsspeicher." source={source}>
      <input id="analysis-workers" aria-label="CPU-Worker" min="1" max="64" type="number" value={value} disabled={lockedByEnvironment} onChange={(event) => onChange({ cpu_workers: Number(event.target.value) })} />
    </SettingField>
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
  const cpuWorkerLocked = sources['analysis.cpu_workers'] === 'env' || sources['analysis.workers'] === 'env'
  const updateAnalysis = (patch: Partial<AppSettings['analysis']>) =>
    setDraft({ ...draft, analysis: { ...analysis, ...patch } })
  const updateThreshold = (
    key: 'genre_threshold' | 'mood_threshold',
    percentage: number,
  ) => {
    const threshold = percentageToThreshold(percentage)
    if (threshold !== null) updateAnalysis({ [key]: threshold })
  }

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
          <ModelStatus models={capabilities.models} />
        </section>

        <section className="panel settings-section" aria-labelledby="analysis-heading">
          <div className="section-heading"><div><p className="eyebrow">Standardwerte</p><h2 id="analysis-heading">Analyse</h2></div></div>
          <div className="form-grid">
            <CpuWorkerField analysis={analysis} sources={sources} onChange={updateAnalysis} />
            <SettingField id="max-audio-seconds" label="Maximale Audiolänge" explanation="Begrenzt den pro Titel ausgewerteten Audioausschnitt. Kürzere Werte sparen Zeit, können aber weniger repräsentativ sein." source={sources['analysis.max_audio_seconds']}>
              <span className="input-with-unit"><input id="max-audio-seconds" min="1" max="3600" type="number" value={analysis.max_audio_seconds} disabled={sources['analysis.max_audio_seconds'] === 'env'} onChange={(event) => updateAnalysis({ max_audio_seconds: Number(event.target.value) })} /><span>Sek.</span></span>
            </SettingField>
            <SettingField id="genre-count" label="Maximale Genres" explanation="Obergrenze für die sichtbaren Genres nach der Aufteilung. Die Schwelle kann zu weniger Vorschlägen führen." source={sources['analysis.genre_count']}>
              <input id="genre-count" min="1" max="20" type="number" value={analysis.genre_count} disabled={sources['analysis.genre_count'] === 'env'} onChange={(event) => updateAnalysis({ genre_count: Number(event.target.value) })} />
            </SettingField>
            <SettingField id="genre-threshold" label="Genre-Schwelle" explanation="Mindest-Vertrauenswert für ein Genre. Ein höherer Wert liefert weniger, dafür sicherere Vorschläge." source={sources['analysis.genre_threshold']}>
              <span className="input-with-unit"><input id="genre-threshold" min="0" max="100" step="1" type="number" value={thresholdToPercentage(analysis.genre_threshold)} disabled={sources['analysis.genre_threshold'] === 'env'} onChange={(event) => updateThreshold('genre_threshold', event.currentTarget.valueAsNumber)} /><span>%</span></span>
            </SettingField>
            <SettingField id="mood-threshold" label="Mood-Schwelle" explanation="Mindest-Vertrauenswert für eine Stimmung. Mood-Werte sind anders skaliert als Genres und deshalb meist deutlich niedriger." source={sources['analysis.mood_threshold']}>
              <span className="input-with-unit"><input id="mood-threshold" min="0" max="100" step="1" type="number" value={thresholdToPercentage(analysis.mood_threshold)} disabled={sources['analysis.mood_threshold'] === 'env'} onChange={(event) => updateThreshold('mood_threshold', event.currentTarget.valueAsNumber)} /><span>%</span></span>
            </SettingField>
          </div>
          <label className="check-row"><input type="checkbox" checked={analysis.write_confidence_tags} disabled={sources['analysis.write_confidence_tags'] === 'env'} onChange={(event) => updateAnalysis({ write_confidence_tags: event.target.checked })} />Konfidenzwerte in verwaltete Tags schreiben</label>
          <label className="check-row"><input type="checkbox" checked={analysis.overwrite_existing} disabled={sources['analysis.overwrite_existing'] === 'env'} onChange={(event) => updateAnalysis({ overwrite_existing: event.target.checked })} />Bestehende verwaltete Tags standardmäßig ersetzen</label>
          <CudaTuning analysis={analysis} sources={sources} onChange={updateAnalysis} enabled={capabilities.available_compute.includes('cuda')} />
        </section>
      </div>

      <BenchmarkPanel
        workerLocked={cpuWorkerLocked}
        onApplied={(saved) => {
          setEffective(saved)
          setDraft(saved.values)
        }}
      />

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
