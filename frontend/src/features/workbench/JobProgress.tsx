import type { JobRecord } from '../jobs/types'
import type { JobEventPayload } from '../jobs/useJobEvents'

interface Props {
  event: JobEventPayload | null
  job: JobRecord
  label: string
}

function progressValue(value: unknown, fallback: number): number {
  return Number(value ?? fallback)
}

function connectionMessage(event: JobEventPayload | null): string | null {
  if (event?.kind !== 'connection_error') return null
  return String(event.payload.message ?? 'Fortschrittsverbindung unterbrochen.')
}

export function JobProgress({ event, job, label }: Props) {
  const total = progressValue(event?.payload.total_items, job.total_items)
  const completed = progressValue(event?.payload.completed_items, job.completed_items)
  const failed = progressValue(event?.payload.failed_items, job.failed_items)
  const succeeded = Math.max(0, completed - failed)
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0
  const errorMessage = connectionMessage(event)

  return (
    <section className="job-progress panel" aria-live="polite">
      <div className="job-progress__heading">
        <strong>{label} läuft</strong>
        <span>{percent} %</span>
      </div>
      <div
        aria-label={`${label}fortschritt`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={percent}
        className="job-progress__track"
        role="progressbar"
      >
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="job-progress__counts">
        <span>{completed} von {total} verarbeitet</span>
        <span>{succeeded} erfolgreich</span>
        <span data-error={failed > 0}>{failed} fehlgeschlagen</span>
      </div>
      {errorMessage && <p className="notice notice--error">{errorMessage}</p>}
    </section>
  )
}
