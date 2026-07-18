import { useCallback, useEffect, useState } from 'react'
import { Cpu, Gauge, MemoryStick, Play, Zap } from 'lucide-react'

import { ApiError, apiRequest } from '../../api/client'
import type { BenchmarkMeasurement, BenchmarkRun, EffectiveSettings, JobResponse } from '../../api/types'

interface BenchmarkPanelProps {
  onApplied: (settings: EffectiveSettings) => void
  workerLocked?: boolean
}

const terminalStatuses = new Set(['completed', 'completed_with_errors', 'failed', 'cancelled'])

function seconds(value: number) {
  return `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} s`
}

function memory(bytes: number) {
  return `${(bytes / 1024 ** 3).toLocaleString('de-DE', { maximumFractionDigits: 2 })} GB`
}

function MeasurementCard({ measurement }: { measurement: BenchmarkMeasurement }) {
  return (
    <article className="benchmark-measurement">
      <div className="benchmark-measurement__title">
        {measurement.compute === 'cuda' ? <Zap aria-hidden="true" size={17} /> : <Cpu aria-hidden="true" size={17} />}
        <strong>{measurement.compute.toUpperCase()}</strong>
      </div>
      <span className="benchmark-measurement__value">{seconds(measurement.average_seconds)}</span>
      <small>für 60 Sekunden Audio</small>
      <dl>
        <div><dt>Start</dt><dd>{seconds(measurement.initialization_seconds)}</dd></div>
        <div><dt>RAM je Worker</dt><dd>{memory(measurement.worker_peak_bytes)}</dd></div>
      </dl>
    </article>
  )
}

// The score reflects independent render states, not nested business decisions.
// eslint-disable-next-line complexity
export function BenchmarkPanel({ onApplied, workerLocked = false }: BenchmarkPanelProps) {
  const [runs, setRuns] = useState<BenchmarkRun[]>([])
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [systemBusy, setSystemBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [applying, setApplying] = useState(false)
  const [message, setMessage] = useState('')

  const loadBenchmarks = useCallback(async () => {
    const loaded = await apiRequest<BenchmarkRun[]>('/api/benchmarks')
    setRuns(loaded)
    return loaded
  }, [])

  const loadJobs = useCallback(async () => {
    const jobs = await apiRequest<JobResponse[]>('/api/jobs')
    setSystemBusy(jobs.some((job) => !terminalStatuses.has(job.status)))
  }, [])

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<BenchmarkRun[]>('/api/benchmarks'),
      apiRequest<JobResponse[]>('/api/jobs'),
    ])
      .then(([loadedRuns, jobs]) => {
        if (!active) return
        setRuns(loadedRuns)
        setSystemBusy(jobs.some((job) => !terminalStatuses.has(job.status)))
      })
      .catch((error: unknown) => {
        if (active) setMessage(error instanceof Error ? error.message : 'Benchmarkdaten fehlen.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!activeJobId) return
    const timer = window.setInterval(async () => {
      try {
        const job = await apiRequest<JobResponse>(`/api/jobs/${activeJobId}`)
        if (!terminalStatuses.has(job.status)) return
        window.clearInterval(timer)
        setActiveJobId(null)
        await Promise.all([loadBenchmarks(), loadJobs()])
      } catch (error) {
        setMessage(error instanceof Error ? error.message : 'Benchmarkstatus konnte nicht geladen werden.')
      }
    }, 800)
    return () => window.clearInterval(timer)
  }, [activeJobId, loadBenchmarks, loadJobs])

  async function startBenchmark() {
    setMessage('')
    setSystemBusy(true)
    try {
      const job = await apiRequest<JobResponse>('/api/benchmarks', { method: 'POST' })
      setActiveJobId(job.id)
      const loaded = await loadBenchmarks()
      if (loaded[0] && terminalStatuses.has(loaded[0].status)) {
        setActiveJobId(null)
        setSystemBusy(false)
      }
    } catch (error) {
      setSystemBusy(false)
      setMessage(error instanceof ApiError ? error.message : 'Benchmark konnte nicht starten.')
    }
  }

  async function applyRecommendation(run: BenchmarkRun) {
    setApplying(true)
    setMessage('')
    try {
      const settings = await apiRequest<EffectiveSettings>(`/api/benchmarks/${run.id}/apply`, {
        method: 'POST',
      })
      onApplied(settings)
      setMessage(`${run.recommended_workers} Worker wurden übernommen.`)
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : 'Empfehlung konnte nicht übernommen werden.')
    } finally {
      setApplying(false)
    }
  }

  const latest = runs[0]
  const cpu = latest?.measurements.find((item) => item.compute === 'cpu')
  const cuda = latest?.measurements.find((item) => item.compute === 'cuda')
  const speedup = cpu && cuda ? cpu.average_seconds / cuda.average_seconds : null
  const running = Boolean(activeJobId) || latest?.status === 'running'
  const canApply = Boolean(
    latest?.status === 'completed' && latest.current && latest.recommended_workers && !workerLocked,
  )

  return (
    <section className="panel settings-section benchmark-panel" aria-labelledby="benchmark-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Leistung automatisch abstimmen</p>
          <h2 id="benchmark-heading">Ressourcen-Benchmark</h2>
        </div>
        <button className="primary-button" type="button" disabled={loading || systemBusy || running} onClick={startBenchmark}>
          <Play aria-hidden="true" size={16} /> {running ? 'Benchmark läuft …' : 'Benchmark starten'}
        </button>
      </div>
      <p className="section-copy benchmark-intro">
        Misst einen geeigneten Titel in einem isolierten Prozess. Einstellungen und Musikdateien werden dabei nicht verändert.
      </p>
      {message && <p className="notice">{message}</p>}

      {!loading && !latest && <div className="benchmark-empty"><Gauge size={22} /><span>Noch keine Messung vorhanden.</span></div>}

      {latest && (
        <div className="benchmark-result">
          <div className="benchmark-summary">
            <div>
              <span className="benchmark-status" data-status={latest.current ? latest.status : 'stale'}>
                {latest.status === 'running' ? 'Messung läuft' : latest.current ? 'Aktuelle Messung' : 'Veraltet'}
              </span>
              <h3>{latest.recommended_workers ? `Empfohlen: ${latest.recommended_workers} Worker` : 'Benchmark-Ergebnis'}</h3>
              <p><strong>Testtitel:</strong> <span>{latest.sample_relative_path ?? 'Wird ausgewählt'}</span> · {latest.sample_seconds} Sekunden</p>
            </div>
            {latest.recommended_workers && (
              <button
                className="benchmark-apply"
                type="button"
                disabled={!canApply || applying}
                onClick={() => applyRecommendation(latest)}
              >
                {latest.recommended_workers} Worker übernehmen
              </button>
            )}
          </div>

          {!latest.current && latest.status === 'completed' && (
            <p className="benchmark-warning">Dieses Ergebnis passt nicht mehr zur aktuellen Umgebung oder Analysekonfiguration. Bitte neu messen.</p>
          )}
          {workerLocked && latest.current && (
            <p className="benchmark-warning">Die Workerzahl ist durch eine Umgebungsvariable festgelegt und kann hier nicht überschrieben werden.</p>
          )}
          {latest.error && <p className="benchmark-warning">{latest.error}</p>}

          <div className="benchmark-measurements">
            {cpu && <MeasurementCard measurement={cpu} />}
            {cuda && <MeasurementCard measurement={cuda} />}
            {speedup && speedup > 0 && (
              <article className="benchmark-speedup">
                <Zap aria-hidden="true" size={18} />
                <strong>CUDA {speedup.toLocaleString('de-DE', { maximumFractionDigits: 1 })}× schneller</strong>
                <span>als CPU in dieser Messung</span>
              </article>
            )}
          </div>

          <div className="benchmark-resources">
            <MemoryStick aria-hidden="true" size={17} />
            <span>Zugewiesen: <strong>{memory(Number(latest.snapshot.memory_bytes ?? 0))} RAM</strong></span>
            <span>Reserve: <strong>{String(latest.snapshot.safety_margin_percent ?? 30)} %</strong></span>
            {latest.finished_at && <span>Gemessen: <strong>{new Date(latest.finished_at).toLocaleString('de-DE')}</strong></span>}
          </div>
        </div>
      )}
    </section>
  )
}
