import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Cpu, Database, FolderOpen, Save } from 'lucide-react'

import { ApiError, apiRequest } from '../../api/client'
import type { AppSettings, Capabilities, PathCapability } from '../../api/types'

const statusLabels = {
  ready: 'Bereit',
  read_only: 'Nur lesen',
  missing: 'Fehlt',
}

interface PathStatusProps {
  icon: typeof FolderOpen
  label: string
  capability: PathCapability
}

function PathStatus({ icon: Icon, label, capability }: PathStatusProps) {
  return (
    <article className="path-status">
      <Icon aria-hidden="true" size={19} />
      <div>
        <span>{label}</span>
        <code>{capability.path}</code>
      </div>
      <span className="status-label" data-status={capability.status}>
        {statusLabels[capability.status]}
      </span>
    </article>
  )
}

export function SettingsView() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true

    Promise.all([
      apiRequest<AppSettings>('/api/settings'),
      apiRequest<Capabilities>('/api/capabilities'),
    ])
      .then(([loadedSettings, loadedCapabilities]) => {
        if (active) {
          setSettings(loadedSettings)
          setCapabilities(loadedCapabilities)
        }
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : 'Einstellungen fehlen.')
      })

    return () => {
      active = false
    }
  }, [])

  async function saveSettings() {
    if (!settings) return
    setMessage('')

    try {
      const saved = await apiRequest<AppSettings>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      })
      setSettings(saved)
      setMessage('Änderungen gespeichert.')
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Speichern fehlgeschlagen.')
    }
  }

  if (!settings || !capabilities) {
    return <div className="panel loading-panel">Einstellungen werden geladen …</div>
  }

  const isCudaImage = capabilities.image_variant === 'cuda'

  return (
    <div className="view-stack">
      <header className="view-heading">
        <div>
          <p className="eyebrow">System & Analyse</p>
          <h1>Einstellungen</h1>
          <p>Pfade prüfen, Analysegrenzen setzen und die verfügbare Rechenart wählen.</p>
        </div>
        <button className="primary-button" onClick={saveSettings} type="button">
          <Save aria-hidden="true" size={17} />
          Änderungen speichern
        </button>
      </header>

      {message && <p className="notice">{message}</p>}

      <section className="panel settings-section" aria-labelledby="storage-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Speicherorte</p>
            <h2 id="storage-heading">Eingebundene Verzeichnisse</h2>
          </div>
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
            <div>
              <p className="eyebrow">Rechenart</p>
              <h2 id="compute-heading">{isCudaImage ? 'CUDA-Image' : 'CPU-Image'}</h2>
            </div>
            <Cpu aria-hidden="true" className="section-icon" size={23} />
          </div>
          <p className="section-copy">
            {isCudaImage
              ? 'Dieses Image kann CPU oder eine erkannte NVIDIA-GPU verwenden.'
              : 'Dieses Image analysiert lokal auf der CPU. Für NVIDIA-GPUs ist das CUDA-Image nötig.'}
          </p>
          <label className="field-label" htmlFor="compute-preference">
            Bevorzugte Rechenart
          </label>
          <select
            id="compute-preference"
            value={settings.compute_preference}
            onChange={(event) =>
              setSettings({
                ...settings,
                compute_preference: event.target.value as AppSettings['compute_preference'],
              })
            }
          >
            <option value="auto">Automatisch</option>
            <option value="cpu">CPU</option>
            <option value="cuda" disabled={!capabilities.available_compute.includes('cuda')}>
              NVIDIA CUDA
            </option>
          </select>
          <div className="model-status">
            {capabilities.models.length ? <Check size={17} /> : <AlertTriangle size={17} />}
            <span>
              <strong>Geladene Modelle</strong>
              {capabilities.models.length
                ? capabilities.models.map((model) => model.name).join(', ')
                : 'Werden mit dem Analysemodul erkannt.'}
            </span>
          </div>
        </section>

        <section className="panel settings-section" aria-labelledby="analysis-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Standardwerte</p>
              <h2 id="analysis-heading">Analyse</h2>
            </div>
          </div>
          <div className="form-grid">
            <label>
              Worker
              <input
                min="1"
                max="64"
                type="number"
                value={settings.worker_count}
                onChange={(event) =>
                  setSettings({ ...settings, worker_count: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Maximale Audiolänge
              <span className="input-with-unit">
                <input
                  min="1"
                  max="3600"
                  type="number"
                  value={settings.max_audio_seconds}
                  onChange={(event) =>
                    setSettings({ ...settings, max_audio_seconds: Number(event.target.value) })
                  }
                />
                <span>Sek.</span>
              </span>
            </label>
            <label>
              Anzahl Genres
              <input
                min="1"
                max="20"
                type="number"
                value={settings.genre_count}
                onChange={(event) =>
                  setSettings({ ...settings, genre_count: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Genre-Schwelle
              <input
                min="0"
                max="1"
                step="0.001"
                type="number"
                value={settings.genre_threshold}
                onChange={(event) =>
                  setSettings({ ...settings, genre_threshold: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Mood-Schwelle
              <input
                min="0"
                max="1"
                step="0.001"
                type="number"
                value={settings.mood_threshold}
                onChange={(event) =>
                  setSettings({ ...settings, mood_threshold: Number(event.target.value) })
                }
              />
            </label>
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={settings.write_confidence_tags}
              onChange={(event) =>
                setSettings({ ...settings, write_confidence_tags: event.target.checked })
              }
            />
            Konfidenzwerte in verwaltete Tags schreiben
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={settings.overwrite_existing}
              onChange={(event) =>
                setSettings({ ...settings, overwrite_existing: event.target.checked })
              }
            />
            Bestehende verwaltete Tags standardmäßig ersetzen
          </label>
        </section>
      </div>
    </div>
  )
}
