import { useEffect, useState } from 'react'
import { AlertTriangle, Check, X } from 'lucide-react'

import { ApiError, apiRequest } from '../../api/client'
import type { WriteOperation } from '../jobs/types'
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
  onWritten: (operations: WriteOperation[]) => void
}

export function WritePreviewDialog({ selection, onClose, onWritten }: Props) {
  const [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [writing, setWriting] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    apiRequest<Preview>('/api/writes/preview', {
      method: 'POST',
      body: JSON.stringify({ selection }),
      signal: controller.signal,
    })
      .then((nextPreview) => {
        setPreview(nextPreview)
        setError(null)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setError(error instanceof ApiError ? error.message : 'Die Vorschau konnte nicht geladen werden.')
      })
    return () => controller.abort()
  }, [selection])

  async function confirm() {
    setWriting(true)
    const response = await apiRequest<{ operations: WriteOperation[] }>('/api/writes', {
      method: 'POST',
      body: JSON.stringify({ selection }),
    })
    onWritten(response.operations)
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
        {error ? (
          <p className="notice notice--error">{error}</p>
        ) : !preview ? (
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
            <footer>
              <button onClick={onClose} type="button">Abbrechen</button>
              <button className="primary-button" disabled={writing || preview.writable === 0} onClick={confirm} type="button">
                {writing ? 'Schreibe …' : 'Schreiben bestätigen'}
              </button>
            </footer>
          </>
        )}
      </section>
    </div>
  )
}
