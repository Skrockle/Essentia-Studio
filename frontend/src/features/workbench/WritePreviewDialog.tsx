import { useEffect, useState } from 'react'
import { AlertTriangle, Check, X } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { JobItemRecord, JobRecord } from '../jobs/types'
import { useJobEvents } from '../jobs/useJobEvents'
import { JobProgress } from './JobProgress'
import type { SelectionSpec } from './types'

interface PreviewItem {
  result_id: string
  relative_path: string
  before_genres: string[]
  after_genres: string[]
  before_moods: string[]
  after_moods: string[]
  conflict: boolean
}

interface Preview {
  total: number
  writable: number
  conflicts: number
  items: PreviewItem[]
}

interface Props {
  selection: SelectionSpec
  onClose: () => void
  onCompleted: (summary: WriteJobSummary) => void
}

export interface WriteJobSummary {
  verified: number
  failed: Array<{ relativePath: string; error: string }>
}

export function WritePreviewDialog({ selection, onClose, onCompleted }: Props) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [writeJob, setWriteJob] = useState<JobRecord | null>(null)
  const [summary, setSummary] = useState<WriteJobSummary | null>(null)
  const writeEvent = useJobEvents(writeJob?.id ?? null)

  useEffect(() => {
    const controller = new AbortController()
    apiRequest<Preview>('/api/writes/preview', {
      method: 'POST',
      body: JSON.stringify({ selection }),
      signal: controller.signal,
    })
      .then(setPreview)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) throw error
      })
    return () => controller.abort()
  }, [selection])

  useEffect(() => {
    if (writeEvent?.kind !== 'terminal' || !writeJob || summary) return
    queueMicrotask(async () => {
      const items = await apiRequest<JobItemRecord[]>(`/api/jobs/${writeJob.id}/items`)
      const nextSummary: WriteJobSummary = {
        verified: items.filter((item) => item.status === 'completed').length,
        failed: items
          .filter((item) => item.status === 'failed')
          .map((item) => ({
            relativePath: item.value,
            error: item.error ?? 'Die Tags konnten nicht geschrieben werden.',
          })),
      }
      setSummary(nextSummary)
      onCompleted(nextSummary)
    })
  }, [onCompleted, summary, writeEvent, writeJob])

  async function confirm() {
    setWriteJob(await apiRequest<JobRecord>('/api/writes/jobs', {
      method: 'POST',
      body: JSON.stringify({ selection }),
    }))
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section aria-labelledby="write-preview-title" aria-modal="true" className="write-dialog" role="dialog">
        <header>
          <div>
            <p className="eyebrow">Letzte Prüfung</p>
            <h2 id="write-preview-title">Tag-Änderungen schreiben</h2>
          </div>
          <button aria-label="Vorschau schließen" onClick={onClose} type="button">
            <X aria-hidden="true" size={18} />
          </button>
        </header>
        {!preview ? (
          <p>Vorschau wird geladen …</p>
        ) : (
          <>
            <div className="preview-counts">
              <span><Check size={15} /> {preview.writable} schreibbar</span>
              <span data-conflicts={preview.conflicts > 0}>
                <AlertTriangle size={15} /> {preview.conflicts} Konflikte
              </span>
            </div>
            <div className="preview-list">
              {preview.items.map((item) => (
                <article data-conflict={item.conflict} key={item.result_id}>
                  <code>{item.relative_path}</code>
                  <p><span>Genre</span> {item.before_genres.join(', ') || '—'} → <strong>{item.after_genres.join(', ') || '—'}</strong></p>
                  <p><span>Mood</span> {item.before_moods.join(', ') || '—'} → <strong>{item.after_moods.join(', ') || '—'}</strong></p>
                </article>
              ))}
            </div>
            {writeJob && !summary && (
              <JobProgress event={writeEvent} job={writeJob} label="Schreibvorgang" />
            )}
            {summary && summary.failed.length > 0 && (
              <div className="notice notice--error">
                <strong>{summary.failed.length} fehlgeschlagen</strong>
                {summary.failed.map((item) => (
                  <p key={item.relativePath}><code>{item.relativePath}</code>: {item.error}</p>
                ))}
              </div>
            )}
            <footer>
              <button onClick={onClose} type="button">Abbrechen</button>
              <button className="primary-button" disabled={Boolean(writeJob) || preview.writable === 0} onClick={confirm} type="button">
                {writeJob ? 'Schreibvorgang läuft …' : 'Schreiben bestätigen'}
              </button>
            </footer>
          </>
        )}
      </section>
    </div>
  )
}
