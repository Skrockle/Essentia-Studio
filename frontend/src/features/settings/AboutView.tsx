import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { Capabilities, HealthResponse } from '../../api/types'

const LICENSE_NOTICES = [
  {
    name: 'Essentia Studio',
    license: 'MIT',
    href: 'https://github.com/Skrockle/Essentia-Studio',
  },
  {
    name: 'Essentia',
    license: 'AGPL-3.0',
    href: 'https://github.com/MTG/essentia',
  },
  {
    name: 'Vortrainierte MTG-Modelle',
    license: 'CC BY-NC-ND 4.0 · ausschließlich nichtkommerziell',
    href: 'https://essentia.upf.edu/models.html',
  },
] as const

const UPSTREAMS = [
  {
    label: 'WB2024/Essentia-to-Metadata',
    href: 'https://github.com/WB2024/Essentia-to-Metadata',
  },
  {
    label: 'WB2024/Navidrome-SmartPlaylist-Generator-nsp',
    href: 'https://github.com/WB2024/Navidrome-SmartPlaylist-Generator-nsp',
  },
] as const

export function AboutView() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<HealthResponse>('/health'),
      apiRequest<Capabilities>('/api/capabilities'),
    ])
      .then(([loadedHealth, loadedCapabilities]) => {
        if (active) {
          setHealth(loadedHealth)
          setCapabilities(loadedCapabilities)
        }
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="view-stack narrow-view">
      <header className="view-heading">
        <div>
          <p className="eyebrow">Version {health?.version ?? 'wird geladen'}</p>
          <h1>Über Essentia Studio</h1>
          <p>Lokale Genre-, Mood- und Smart-Playlist-Werkzeuge für deine Mediathek.</p>
        </div>
      </header>

      <section className="panel about-panel">
        <p className="about-lead">
          Diese Installation läuft als <strong>{capabilities?.image_variant ?? '…'}-Image</strong>.
          Analysevorschläge werden erst nach deiner Auswahl in Audiodateien geschrieben.
        </p>
        <dl className="fact-list">
          {LICENSE_NOTICES.map((notice) => (
            <div key={notice.name}>
              <dt>{notice.name}</dt>
              <dd>
                <a href={notice.href} rel="noreferrer" target="_blank">
                  {notice.license} <ExternalLink aria-hidden="true" size={14} />
                </a>
              </dd>
            </div>
          ))}
        </dl>
        <p className="notice warning-notice">
          Die mitgelieferten Modelle dürfen wegen CC BY-NC-ND 4.0 nicht kommerziell genutzt
          oder verändert weitergegeben werden.
        </p>
        <div className="about-links">
          {UPSTREAMS.map((upstream) => (
            <a key={upstream.href} href={upstream.href} rel="noreferrer" target="_blank">
              {upstream.label} <ExternalLink aria-hidden="true" size={15} />
            </a>
          ))}
        </div>
      </section>
    </div>
  )
}
