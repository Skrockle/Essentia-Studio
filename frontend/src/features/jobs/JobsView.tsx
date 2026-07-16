import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, CircleDot, History, RotateCcw, TriangleAlert } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { JobRecord, WriteOperation } from './types'
import { useJobEvents } from './useJobEvents'

const runningStatuses = new Set(['queued', 'running'])

export function JobsView() {
  const [jobs, setJobs] = useState<JobRecord[]>([])
  const [writes, setWrites] = useState<WriteOperation[]>([])
  const activeJob = jobs.find((job) => runningStatuses.has(job.status)) ?? null
  const event = useJobEvents(activeJob?.id ?? null)

  const load = useCallback(async () => {
    const [nextJobs, nextWrites] = await Promise.all([
      apiRequest<JobRecord[]>('/api/jobs'),
      apiRequest<WriteOperation[]>('/api/writes'),
    ])
    setJobs(nextJobs)
    setWrites(nextWrites)
  }, [])

  useEffect(() => {
    void Promise.all([
      apiRequest<JobRecord[]>('/api/jobs'),
      apiRequest<WriteOperation[]>('/api/writes'),
    ]).then(([nextJobs, nextWrites]) => {
      setJobs(nextJobs)
      setWrites(nextWrites)
    })
  }, [])

  useEffect(() => {
    if (event?.kind !== 'terminal') return
    void Promise.all([
      apiRequest<JobRecord[]>('/api/jobs'),
      apiRequest<WriteOperation[]>('/api/writes'),
    ]).then(([nextJobs, nextWrites]) => {
      setJobs(nextJobs)
      setWrites(nextWrites)
    })
  }, [event])

  async function undo(operation: WriteOperation) {
    await apiRequest(`/api/writes/${operation.id}/undo`, { method: 'POST' })
    await load()
  }

  return (
    <div className="view-stack">
      <header className="view-heading">
        <div>
          <p className="eyebrow">Nachvollziehbar und reversibel</p>
          <h1>Jobs &amp; Verlauf</h1>
          <p>Scans, Analysen, Fehler und verifizierte Schreibvorgänge an einem Ort.</p>
        </div>
      </header>

      <section className="panel history-panel">
        <div className="section-heading"><h2>Verarbeitung</h2><History size={19} /></div>
        {jobs.length === 0 ? <p className="section-copy">Noch keine Jobs.</p> : (
          <div className="history-list">
            {jobs.map((job) => (
              <article key={job.id}>
                {runningStatuses.has(job.status) ? <CircleDot size={17} /> : job.failed_items > 0 ? <TriangleAlert size={17} /> : <CheckCircle2 size={17} />}
                <div><strong>{job.type}</strong><span>{job.completed_items} / {job.total_items} · {job.status}</span></div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel history-panel">
        <div className="section-heading"><h2>Tag-Schreibvorgänge</h2><RotateCcw size={19} /></div>
        {writes.length === 0 ? <p className="section-copy">Noch keine Tags geschrieben.</p> : (
          <div className="history-list">
            {writes.map((operation) => (
              <article key={operation.id}>
                {operation.status === 'verified' ? <CheckCircle2 size={17} /> : <TriangleAlert size={17} />}
                <div><code>{operation.relative_path}</code><span>{operation.error_message ?? operation.status}</span></div>
                {operation.undo_available && (
                  <button onClick={() => undo(operation)} type="button">Tags wiederherstellen</button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
