import { Ban, ChevronUp, CircleDot, Clock3 } from 'lucide-react'

import type { JobRecord } from './types'

const jobLabels: Record<JobRecord['type'], string> = {
  analysis: 'Analyse',
  scan: 'Scan',
  write: 'Schreiben',
  undo: 'Wiederherstellen',
  playlist_write: 'Playlist speichern',
  benchmark: 'Benchmark',
}

interface Props {
  activeJob: JobRecord
  cancellingJobId?: string | null
  etaSeconds: number | null
  expanded: boolean
  jobs: JobRecord[]
  onCancel: (jobId: string) => void | Promise<void>
  onToggle: () => void
}

export function JobStatusBar({
  activeJob,
  cancellingJobId = null,
  etaSeconds,
  expanded,
  jobs,
  onCancel,
  onToggle,
}: Props) {
  const percent = activeJob.total_items > 0
    ? Math.round((activeJob.completed_items / activeJob.total_items) * 100)
    : 0
  const cancelling = cancellingJobId === activeJob.id || activeJob.cancel_requested

  return (
    <aside className="job-status" aria-label="Aktueller Job">
      <div className="job-status__bar">
        <button
          aria-expanded={expanded}
          className="job-status__summary"
          onClick={onToggle}
          type="button"
        >
          <CircleDot aria-hidden="true" className="job-status__pulse" size={17} />
          <strong>{jobLabels[activeJob.type]}</strong>
          <span>{activeJob.completed_items} / {activeJob.total_items}</span>
          <span className="job-status__percent">{percent}%</span>
          <span className="job-status__eta">
            <Clock3 aria-hidden="true" size={14} />
            {formatEta(etaSeconds)}
          </span>
        </button>
        <button
          aria-label="Job abbrechen"
          className="job-status__cancel"
          disabled={Boolean(cancelling)}
          onClick={() => void onCancel(activeJob.id)}
          type="button"
        >
          <Ban aria-hidden="true" size={15} />
          {cancelling ? 'Abbruch angefordert …' : 'Abbrechen'}
        </button>
        <button
          aria-label={expanded ? 'Jobdetails schließen' : 'Jobdetails öffnen'}
          className="job-status__toggle"
          onClick={onToggle}
          type="button"
        >
          <ChevronUp aria-hidden="true" size={17} />
        </button>
      </div>
      <div className="job-status__track" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>
      {expanded && (
        <div className="job-status__details">
          {jobs.filter((job) => job.status === 'queued' || job.status === 'running').map((job) => (
            <div key={job.id}>
              <span>{jobLabels[job.type]}</span>
              <span>{job.completed_items} / {job.total_items} · {job.status === 'running' ? 'läuft' : 'wartet'}</span>
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}

function formatEta(seconds: number | null) {
  if (seconds === null) return 'Restzeit wird berechnet …'
  if (seconds < 60) return 'Restzeit < 1 min'
  const minutes = Math.ceil(seconds / 60)
  if (minutes < 60) return `Restzeit ca. ${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return remainingMinutes > 0
    ? `Restzeit ca. ${hours} h ${remainingMinutes} min`
    : `Restzeit ca. ${hours} h`
}
