import { useEffect, useRef, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { JobRecord } from './types'

export interface JobEventPayload {
  sequence: number
  kind: string
  payload: Record<string, unknown>
}

export function useJobEvents(jobId: string | null) {
  const [eventState, setEventState] = useState<{
    jobId: string
    event: JobEventPayload
  } | null>(null)
  const lastSequence = useRef(0)

  useEffect(() => {
    lastSequence.current = 0
    if (!jobId) return
    const currentJobId = jobId
    const source = new EventSource(`/api/jobs/${currentJobId}/events?after=${lastSequence.current}`)
    let active = true

    function receive(event: MessageEvent<string>) {
      const parsed = JSON.parse(event.data) as JobEventPayload
      if (parsed.sequence <= lastSequence.current) return
      lastSequence.current = parsed.sequence
      setEventState({ jobId: currentJobId, event: parsed })
      if (parsed.kind === 'terminal') source.close()
    }

    source.addEventListener('progress', receive as EventListener)
    source.addEventListener('terminal', receive as EventListener)
    source.addEventListener('error', (() => {
      source.close()
      void apiRequest<JobRecord>(`/api/jobs/${currentJobId}`)
        .then((job) => {
          if (!active) return
          if (['completed', 'completed_with_errors', 'cancelled', 'failed'].includes(job.status)) {
            setEventState({
              jobId: currentJobId,
              event: {
                sequence: lastSequence.current + 1,
                kind: 'terminal',
                payload: {
                  total_items: job.total_items,
                  completed_items: job.completed_items,
                  failed_items: job.failed_items,
                  status: job.status,
                },
              },
            })
          } else {
            setEventState({
              jobId: currentJobId,
              event: {
                sequence: lastSequence.current + 1,
                kind: 'connection_error',
                payload: { message: 'Fortschrittsverbindung unterbrochen. Job läuft weiter.' },
              },
            })
          }
        })
        .catch(() => {
          if (active) {
            setEventState({
              jobId: currentJobId,
              event: {
                sequence: lastSequence.current + 1,
                kind: 'connection_error',
                payload: { message: 'Jobstatus konnte nicht erneut geladen werden.' },
              },
            })
          }
        })
    }) as EventListener)
    return () => {
      active = false
      source.close()
    }
  }, [jobId])

  return eventState?.jobId === jobId ? eventState.event : null
}
