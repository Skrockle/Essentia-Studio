import { useEffect, useRef, useState } from 'react'

export interface JobEventPayload {
  sequence: number
  job_id: string
  kind: string
  payload: Record<string, unknown>
}

export function useJobEvents(jobId: string | null) {
  const [lastEvent, setLastEvent] = useState<JobEventPayload | null>(null)
  const lastSequence = useRef(0)

  useEffect(() => {
    if (!jobId) return
    lastSequence.current = 0
    const source = new EventSource(`/api/jobs/${jobId}/events?after=${lastSequence.current}`)

    function receive(event: MessageEvent<string>) {
      const parsed = JSON.parse(event.data) as JobEventPayload
      if (parsed.sequence <= lastSequence.current) return
      lastSequence.current = parsed.sequence
      setLastEvent(parsed)
      if (parsed.kind === 'terminal') source.close()
    }

    source.addEventListener('started', receive as EventListener)
    source.addEventListener('progress', receive as EventListener)
    source.addEventListener('terminal', receive as EventListener)
    return () => source.close()
  }, [jobId])

  return lastEvent
}
