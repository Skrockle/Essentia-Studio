import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import { apiRequest } from '../../api/client'
import { JobStatusBar } from './JobStatusBar'
import type { JobProgress, JobRecord } from './types'
import { useJobEvents } from './useJobEvents'

const activeStatuses = new Set(['queued', 'running'])

interface EtaState {
  startedAt: number
  completed: number
}

interface JobMonitorValue {
  activeJob: JobRecord | null
  etaSeconds: number | null
  jobs: JobRecord[]
  cancelJob: (jobId: string) => Promise<void>
}

const JobMonitorContext = createContext<JobMonitorValue | null>(null)

export function JobMonitorProvider({ children }: { children: React.ReactNode }) {
  const [jobs, setJobs] = useState<JobRecord[]>([])
  const [cancellingJobIds, setCancellingJobIds] = useState<Set<string>>(() => new Set())
  const [etaSeconds, setEtaSeconds] = useState<number | null>(null)
  const etaByJob = useRef(new Map<string, EtaState>())
  const loadJobs = useCallback(async () => {
    try {
      const response = await apiRequest<unknown>('/api/jobs')
      setJobs(Array.isArray(response) ? response as JobRecord[] : [])
    } catch {
      // The status bar must not make the rest of the application unavailable.
    }
  }, [])
  const activeJob = useMemo(
    () => jobs.find((job) => job.status === 'running')
      ?? jobs.find((job) => job.status === 'queued')
      ?? null,
    [jobs],
  )
  const event = useJobEvents(activeJob?.id ?? null)
  const progress = useMemo(
    () => getProgress(activeJob, event),
    [activeJob, event],
  )

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadJobs(), 0)
    const interval = window.setInterval(() => void loadJobs(), 2000)
    return () => {
      window.clearTimeout(initialLoad)
      window.clearInterval(interval)
    }
  }, [loadJobs])

  useEffect(() => {
    if (!event) return
    const current = etaByJob.current.get(event.job_id) ?? {
      startedAt: Date.now(),
      completed: 0,
    }
    const completed = Number(event.payload.completed_items ?? current.completed)
    etaByJob.current.set(event.job_id, { ...current, completed })
    if (event.kind === 'terminal') {
      window.setTimeout(() => void loadJobs(), 0)
    }
  }, [event, loadJobs])

  useEffect(() => {
    for (const job of jobs) {
      if (activeStatuses.has(job.status) && !etaByJob.current.has(job.id)) {
        etaByJob.current.set(job.id, { startedAt: Date.now(), completed: job.completed_items })
      }
    }
  }, [jobs])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setEtaSeconds(calculateEta(activeJob, progress, etaByJob.current))
    }, 0)
    return () => window.clearTimeout(timer)
  }, [activeJob, progress])

  async function cancelJob(jobId: string) {
    setCancellingJobIds((current) => new Set(current).add(jobId))
    try {
      await apiRequest(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
      await loadJobs()
    } finally {
      setCancellingJobIds((current) => {
        const next = new Set(current)
        next.delete(jobId)
        return next
      })
    }
  }

  return (
    <JobMonitorContext.Provider value={{ activeJob, etaSeconds, jobs, cancelJob }}>
      {children}
      <JobStatusSlot
        activeJob={activeJob}
        cancellingJobIds={cancellingJobIds}
        etaSeconds={etaSeconds}
        jobs={jobs}
        onCancel={cancelJob}
      />
    </JobMonitorContext.Provider>
  )
}

function getProgress(
  activeJob: JobRecord | null,
  event: ReturnType<typeof useJobEvents>,
): JobProgress {
  const completed = activeJob?.completed_items ?? 0
  const total = activeJob?.total_items ?? 0
  if (event?.kind !== 'progress') return { completed_items: completed, total_items: total }
  return {
    completed_items: Number(event.payload.completed_items ?? completed),
    total_items: Number(event.payload.total_items ?? total),
  }
}

function calculateEta(
  activeJob: JobRecord | null,
  progress: JobProgress,
  etaByJob: Map<string, EtaState>,
): number | null {
  if (!activeJob || progress.completed_items <= 0 || progress.total_items <= progress.completed_items) {
    return null
  }
  const state = etaByJob.get(activeJob.id)
  if (!state) return null
  const elapsedSeconds = Math.max(1, (Date.now() - state.startedAt) / 1000)
  return Math.ceil(
    ((progress.total_items - progress.completed_items) * elapsedSeconds) / progress.completed_items,
  )
}

function JobStatusSlot({
  activeJob,
  cancellingJobIds,
  etaSeconds,
  jobs,
  onCancel,
}: {
  activeJob: JobRecord | null
  cancellingJobIds: ReadonlySet<string>
  etaSeconds: number | null
  jobs: JobRecord[]
  onCancel: (jobId: string) => Promise<void>
}) {
  const [expanded, setExpanded] = useState(false)
  if (!activeJob) return null
  return (
    <JobStatusBar
      activeJob={activeJob}
      cancellingJobIds={cancellingJobIds}
      etaSeconds={etaSeconds}
      expanded={expanded}
      jobs={jobs}
      onCancel={onCancel}
      onToggle={() => setExpanded((current) => !current)}
    />
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useJobMonitor() {
  const context = useContext(JobMonitorContext)
  if (!context) throw new Error('useJobMonitor must be used within JobMonitorProvider')
  return context
}
