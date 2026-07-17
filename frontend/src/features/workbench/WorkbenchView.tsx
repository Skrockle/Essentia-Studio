import { useEffect, useMemo, useState } from 'react'
import { AudioWaveform, FolderSearch, PenLine, Search, Sparkles } from 'lucide-react'

import { apiRequest } from '../../api/client'
import type { JobRecord } from '../jobs/types'
import { useJobEvents } from '../jobs/useJobEvents'
import { LibraryTable } from './LibraryTable'
import { JobProgress } from './JobProgress'
import { ResultTable } from './ResultTable'
import { SelectionToolbar } from './SelectionToolbar'
import { WorkbenchViewControls } from './WorkbenchViewControls'
import { useResults } from './useResults'
import { useTagOptions } from './useTagOptions'
import { WritePreviewDialog, type WriteJobSummary } from './WritePreviewDialog'
import type { ResultRow } from './types'
import type { TagOptions } from '../../api/types'
import { useLibraryTracks } from './useLibraryTracks'
import {
  loadWorkbenchPreferences,
  saveWorkbenchPreferences,
  type ResultColumn,
} from './viewPreferences'

interface WorkbenchActionsProps {
  active: boolean
  analysisSelectedCount: number
  selectedCount: number
  onScan: () => void
  onAnalyze: () => void
  onPreview: () => void
}

function WorkbenchActions({
  active,
  analysisSelectedCount,
  selectedCount,
  onScan,
  onAnalyze,
  onPreview,
}: WorkbenchActionsProps) {
  return (
    <div className="workbench-actions">
      <button disabled={active} onClick={onScan} type="button">
        <FolderSearch aria-hidden="true" size={16} /> Bibliothek scannen
      </button>
      <button disabled={active || analysisSelectedCount === 0} onClick={onAnalyze} type="button">
        <Sparkles aria-hidden="true" size={16} />
        {analysisSelectedCount > 0 ? `${analysisSelectedCount} Titel analysieren` : 'Auswahl analysieren'}
      </button>
      <button className="primary-button" disabled={!selectedCount || active} onClick={onPreview} type="button">
        <PenLine aria-hidden="true" size={16} /> {selectedCount} Titel schreiben
      </button>
    </div>
  )
}

interface ResultsProps {
  error: string | null
  rows: ResultRow[]
  allSelected: boolean
  onSelectAll: (selected: boolean) => void
  onSelectRow: (row: ResultRow, selected: boolean) => void
  onSaveDraft: (row: ResultRow, genres: string[], moods: string[]) => void
  tagOptions: TagOptions
  visibleColumns: ResultColumn[]
}

function WorkbenchResults({ error, rows, ...tableProps }: ResultsProps) {
  if (error) return <p className="notice notice--error">{error}</p>
  if (rows.length > 0) return <ResultTable rows={rows} {...tableProps} />
  return (
    <section className="panel workbench-empty">
      <div className="empty-icon"><AudioWaveform aria-hidden="true" size={30} /></div>
      <div>
        <p className="eyebrow">Noch keine Vorschläge</p>
        <h2>Scanne und analysiere deine Mediathek</h2>
        <p>Die Ergebnisse erscheinen hier zur Prüfung, ohne deine Dateien zu verändern.</p>
      </div>
    </section>
  )
}

export function WorkbenchView() {
  const [search, setSearch] = useState('')
  const query = useMemo(() => ({ search }), [search])
  const {
    page,
    error,
    selection,
    refresh,
    selectAll,
    selectRow,
    saveDraft,
    bulkUpdate,
  } = useResults(query)
  const {
    tracks: libraryTracks,
    error: libraryError,
    refresh: refreshLibrary,
  } = useLibraryTracks(search)
  const { options: tagOptions, error: tagOptionsError } = useTagOptions()
  const [analysisSelection, setAnalysisSelection] = useState<Set<number>>(new Set())
  const [activeJob, setActiveJob] = useState<JobRecord | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [viewPreferences, setViewPreferences] = useState(loadWorkbenchPreferences)
  const event = useJobEvents(activeJob?.id ?? null)
  const allSelected = page.total > 0 && page.selected_count === page.total
  const availableFormats = useMemo(
    () => [...new Set(libraryTracks.map((track) => track.extension))].sort(),
    [libraryTracks],
  )
  const filteredLibraryTracks = useMemo(
    () => libraryTracks.filter((track) => (
      viewPreferences.statuses.includes(track.processing_state)
      && (viewPreferences.showWritten || track.processing_state !== 'written')
      && (viewPreferences.formats.length === 0 || viewPreferences.formats.includes(track.extension))
    )),
    [libraryTracks, viewPreferences],
  )
  const visibleTrackIds = useMemo(
    () => new Set(filteredLibraryTracks.map((track) => track.id)),
    [filteredLibraryTracks],
  )

  useEffect(() => saveWorkbenchPreferences(viewPreferences), [viewPreferences])
  const visibleAnalysisSelection = useMemo(
    () => new Set([...analysisSelection].filter((id) => visibleTrackIds.has(id))),
    [analysisSelection, visibleTrackIds],
  )

  useEffect(() => {
    if (event?.kind !== 'terminal' || !activeJob) return
    const jobType = activeJob.type
    queueMicrotask(async () => {
      if (jobType === 'scan') {
        const scannedTracks = await refreshLibrary()
        const scannedIds = new Set(scannedTracks.map((track) => track.id))
        setAnalysisSelection((current) =>
          new Set([...current].filter((id) => scannedIds.has(id))),
        )
        setStatusMessage(`Scan abgeschlossen – ${scannedTracks.length} Titel gefunden`)
      } else {
        const failedItems = Number(event.payload.failed_items ?? 0)
        const status = String(event.payload.status ?? '')
        setStatusMessage(
          status === 'completed_with_errors' || failedItems > 0
            ? `Analyse beendet – ${failedItems} ${failedItems === 1 ? 'Titel' : 'Titel'} fehlgeschlagen`
            : status === 'failed'
              ? 'Analyse fehlgeschlagen'
              : status === 'cancelled'
                ? 'Analyse abgebrochen'
                : 'Analyse abgeschlossen',
        )
      }
      setActiveJob(null)
      refresh()
    })
  }, [activeJob, event, refresh, refreshLibrary])

  async function startScan() {
    setStatusMessage(null)
    setActiveJob(await apiRequest<JobRecord>('/api/library/scan', { method: 'POST' }))
  }

  async function startAnalysis() {
    if (visibleAnalysisSelection.size === 0) return
    setStatusMessage(null)
    setActiveJob(
      await apiRequest<JobRecord>('/api/analysis/jobs', {
        method: 'POST',
        body: JSON.stringify({
          track_ids: [...visibleAnalysisSelection].sort((left, right) => left - right),
        }),
      }),
    )
    setAnalysisSelection(new Set())
  }

  function selectAllForAnalysis(selected: boolean) {
    setAnalysisSelection(selected ? new Set(filteredLibraryTracks.map((track) => track.id)) : new Set())
  }

  function selectTrackForAnalysis(trackId: number, selected: boolean) {
    setAnalysisSelection((current) => {
      const next = new Set(current)
      if (selected) next.add(trackId)
      else next.delete(trackId)
      return next
    })
  }

  async function finishWrite(summary: WriteJobSummary) {
    setShowPreview(false)
    setStatusMessage(`${summary.verified} verifiziert`)
    await Promise.all([refresh(), refreshLibrary()])
  }

  return (
    <div className="view-stack">
      <header className="workbench-hero">
        <div>
          <p className="eyebrow">Mediathek-Analyse</p>
          <h1>Aus Klang wird Ordnung.</h1>
          <p>
            Genres und Moods prüfen, manuell verfeinern und erst nach einer Vorschau in die
            Musikdateien schreiben.
          </p>
        </div>
        <div className="signal-wave" aria-hidden="true">
          {[14, 28, 19, 42, 31, 55, 24, 47, 63, 34, 51, 25, 39, 18, 31, 13].map(
            (height, index) => <span key={index} style={{ height }} />,
          )}
        </div>
      </header>

      <section className="workbench-controls panel">
        <label className="search-field">
          <Search aria-hidden="true" size={17} />
          <span className="sr-only">Ergebnisse filtern</span>
          <input
            aria-label="Ergebnisse filtern"
            onChange={(event) => {
              setSearch(event.target.value)
              setAnalysisSelection(new Set())
            }}
            placeholder="Titel oder Pfad filtern …"
            type="search"
            value={search}
          />
        </label>
        <div className="result-summary">
          <Sparkles aria-hidden="true" size={17} />
          <strong>{page.total}</strong> analysierte Titel
        </div>
        <WorkbenchActions
          active={Boolean(activeJob)}
          analysisSelectedCount={visibleAnalysisSelection.size}
          onAnalyze={startAnalysis}
          onPreview={() => setShowPreview(true)}
          onScan={startScan}
          selectedCount={page.selected_count}
        />
      </section>

      {libraryError && <p className="notice notice--error">{libraryError}</p>}
      {tagOptionsError && <p className="notice notice--error">{tagOptionsError}</p>}
      <WorkbenchViewControls
        availableFormats={availableFormats}
        onChange={setViewPreferences}
        value={viewPreferences}
      />
      <LibraryTable
        onSelectAll={selectAllForAnalysis}
        onSelectTrack={selectTrackForAnalysis}
        selectedIds={visibleAnalysisSelection}
        tracks={filteredLibraryTracks}
        visibleColumns={viewPreferences.libraryColumns}
      />

      <SelectionToolbar selectedCount={page.selected_count} onBulkUpdate={bulkUpdate} />

      {activeJob && (
        <JobProgress
          event={event}
          job={activeJob}
          label={activeJob.type === 'scan' ? 'Scan' : 'Analyse'}
        />
      )}
      {statusMessage && <p className="notice notice--success">{statusMessage}</p>}
      <WorkbenchResults
        allSelected={allSelected}
        error={error}
        onSaveDraft={saveDraft}
        onSelectAll={selectAll}
        onSelectRow={selectRow}
        rows={page.items}
        tagOptions={tagOptions}
        visibleColumns={viewPreferences.resultColumns}
      />
      {showPreview && (
        <WritePreviewDialog
          onClose={() => setShowPreview(false)}
          onCompleted={finishWrite}
          selection={selection}
        />
      )}
    </div>
  )
}
