import { ExternalLink } from 'lucide-react'

export function AboutView() {
  return (
    <div className="view-stack narrow-view">
      <header className="view-heading">
        <div>
          <p className="eyebrow">Version 0.0.0</p>
          <h1>Über Essentia Studio</h1>
          <p>Lokale Genre-, Mood- und Smart-Playlist-Werkzeuge für deine Mediathek.</p>
        </div>
      </header>

      <section className="panel about-panel">
        <p className="about-lead">
          Essentia Studio verbindet die Analyse von WB2024/Essentia-to-Metadata mit dem
          Navidrome Smart Playlist Generator in einer gemeinsamen, prüfbaren Oberfläche.
        </p>
        <dl className="fact-list">
          <div>
            <dt>Anwendung</dt>
            <dd>MIT</dd>
          </div>
          <div>
            <dt>Essentia</dt>
            <dd>AGPL-3.0</dd>
          </div>
          <div>
            <dt>Vortrainierte Modelle</dt>
            <dd>CC BY-NC-ND 4.0 · nicht kommerziell</dd>
          </div>
        </dl>
        <a href="https://github.com/WB2024/Essentia-to-Metadata" rel="noreferrer" target="_blank">
          Upstream-Projekt ansehen <ExternalLink aria-hidden="true" size={15} />
        </a>
      </section>
    </div>
  )
}
