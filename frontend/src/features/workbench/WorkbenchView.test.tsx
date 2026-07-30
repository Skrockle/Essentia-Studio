import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { WorkbenchView } from './WorkbenchView'

let selectedCount = 0
let ambientAdded = false
let writeCalls = 0
let analysisBodies: unknown[] = []
let includeWrittenTrack = false
let libraryRequestUrls: string[] = []
let nextLibraryResponse: Promise<Response> | null = null
let useMultiPageLibrary = false

class FakeEventSource {
  static latest: FakeEventSource | null = null
  private listeners = new Map<string, EventListener>()

  constructor() {
    FakeEventSource.latest = this
  }

  addEventListener(type: string, listener: EventListener) {
    this.listeners.set(type, listener)
  }

  emit(type: string, data: object) {
    this.listeners.get(type)?.(new MessageEvent(type, { data: JSON.stringify(data) }))
  }

  close() {}
}

function deferredResponse() {
  let resolve: (response: Response) => void
  let reject: (reason: unknown) => void
  const promise = new Promise<Response>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })
  return { promise, resolve: resolve!, reject: reject! }
}

beforeEach(() => {
  localStorage.clear()
  selectedCount = 0
  ambientAdded = false
  writeCalls = 0
  analysisBodies = []
  includeWrittenTrack = false
  libraryRequestUrls = []
  nextLibraryResponse = null
  useMultiPageLibrary = false
  FakeEventSource.latest = null
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.stubGlobal(
    'fetch',
    // The centralized test fixture intentionally covers every Workbench endpoint.
    // eslint-disable-next-line complexity
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/api/tag-options')) {
        return Response.json({ genres: ['Ambient'], moods: ['Calm'] })
      }
      if (url.includes('/api/library/tracks')) {
        libraryRequestUrls.push(url)
        if (nextLibraryResponse) {
          const pendingResponse = nextLibraryResponse
          nextLibraryResponse = null
          return pendingResponse
        }
        const searchParameters = new URL(url, 'http://localhost').searchParams
        if (useMultiPageLibrary) {
          const page = Number(searchParameters.get('page'))
          const trackIds = page === 1
            ? Array.from({ length: 200 }, (_, index) => index + 1)
            : [201]
          const tracks = trackIds.map((id) => libraryTrack(id, `Library/${id}.flac`))
          return Response.json({ items: tracks, total: 201, page, page_size: 200 })
        }
        const filteredTracks = searchParameters.has('missing_genre') && searchParameters.has('missing_mood')
          ? [libraryTrack(12, 'Library/two.mp3')]
          : searchParameters.has('missing_genre')
            ? [libraryTrack(11, 'Library/one.flac')]
            : [
                {
                  ...libraryTrack(11, 'Library/one.flac'),
                  processing_state: writeCalls > 0 ? 'written' : 'new',
                },
                libraryTrack(12, 'Library/two.mp3'),
                ...(includeWrittenTrack
                  ? [{
                      ...libraryTrack(13, 'Library/written.flac'),
                      artist: 'Archive',
                      title: 'Already Written',
                      processing_state: 'written',
                    }]
                  : []),
              ]
        return Response.json({
          items: filteredTracks,
          total: filteredTracks.length,
          page: 1,
          page_size: 200,
        })
      }
      if (url.includes('/api/analysis/jobs')) {
        analysisBodies.push(JSON.parse(String(init?.body)))
        return Response.json({
          id: 'analysis-1',
          type: 'analysis',
          status: 'queued',
          total_items: 1,
          completed_items: 0,
          failed_items: 0,
        })
      }
      if (url.includes('/api/writes/jobs')) {
        writeCalls += 1
        return Response.json({
          id: 'write-1',
          type: 'write',
          status: 'queued',
          total_items: 1,
          completed_items: 0,
          failed_items: 0,
        })
      }
      if (url.includes('/api/jobs/write-1/items')) {
        return Response.json([
          {
            id: 1,
            job_id: 'write-1',
            position: 0,
            value: 'Artist/one.flac',
            status: 'completed',
            result: {
              operation_id: 'write-1-operation',
              relative_path: 'Artist/one.flac',
              status: 'verified',
            },
            error: null,
          },
        ])
      }
      if (url.includes('/api/jobs/analysis-1')) {
        return Response.json({
          id: 'analysis-1',
          type: 'analysis',
          status: 'completed',
          total_items: 2,
          completed_items: 2,
          failed_items: 0,
        })
      }
      if (url.includes('/api/library/scan')) {
        return Response.json({
          id: 'scan-1',
          type: 'scan',
          status: 'queued',
          total_items: 1,
          completed_items: 0,
          failed_items: 0,
        })
      }
      if (url.includes('/api/results/selection')) {
        selectedCount = 63
        return Response.json({ affected: 63 })
      }
      if (url.includes('/api/writes/preview')) {
        return Response.json({
          total: 63,
          writable: 63,
          conflicts: 0,
          items: [
            {
              result_id: 'one',
              relative_path: 'Artist/one.flac',
              before_genres: ['Rock'],
              after_genres: ['Electronic; House'],
              before_moods: [],
              after_moods: ['Happy'],
              conflict: false,
            },
          ],
        })
      }
      if (url.endsWith('/api/writes')) {
        writeCalls += 1
        return Response.json({
          operations: [
            {
              id: 'write-1',
              result_id: 'one',
              relative_path: 'Artist/one.flac',
              status: 'verified',
              error_code: null,
              error_message: null,
              undo_available: true,
            },
          ],
        })
      }
      if (url.includes('/api/results/bulk-draft')) {
        ambientAdded = true
        return Response.json({ affected: 63 })
      }
      if (url.includes('/api/results')) {
        return Response.json({
          items: [resultRow('one'), resultRow('two')],
          total: 63,
          page: 1,
          page_size: 50,
          selected_count: selectedCount,
        })
      }
      return Response.json({ status: 'completed' })
    }),
  )
})

function libraryTrack(id: number, relativePath: string) {
  return {
    id,
    relative_path: relativePath,
    extension: relativePath.endsWith('.flac') ? '.flac' : '.mp3',
    size: 1024,
    mtime_ns: 1,
    last_seen: '2026-07-17T00:00:00Z',
    present: true,
    artist: id === 11 ? 'Bastille' : 'Underworld',
    title: id === 11 ? 'Quarter Past Midnight' : 'Rez',
    album: id === 11 ? 'Doom Days' : 'Everything, Everything',
    duration_seconds: 180,
    metadata_source: 'embedded',
    processing_state: 'new',
  }
}

test('shows scanned tracks and analyzes only explicitly selected track ids', async () => {
  render(<WorkbenchView />)

  expect((await screen.findAllByText('Quarter Past Midnight')).length).toBeGreaterThan(0)
  expect(screen.getAllByText('Bastille').length).toBeGreaterThan(0)
  expect(screen.getByRole('button', { name: 'Auswahl analysieren' })).toBeDisabled()

  await userEvent.click(screen.getByRole('checkbox', { name: 'Library/one.flac analysieren' }))
  await userEvent.click(screen.getByRole('button', { name: '1 Titel analysieren' }))

  await waitFor(() => expect(analysisBodies).toEqual([{ track_ids: [11] }]))
})

test('keeps the tablet toolbar layout targets grouped by their control roles', async () => {
  render(<WorkbenchView />)

  const controls = (await screen.findByLabelText('Ergebnisse filtern')).closest('.workbench-controls')
  expect(controls).not.toBeNull()
  expect(controls?.querySelector('.search-field')).not.toBeNull()
  expect(controls?.querySelector('.quick-filters')).not.toBeNull()
  expect(controls?.querySelector('.result-summary')).not.toBeNull()
  expect(controls?.querySelector('.workbench-actions')).not.toBeNull()
})

test('reports a partially failed analysis instead of success', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' }),
  )
  await userEvent.click(screen.getByRole('button', { name: '1 Titel analysieren' }))
  await waitFor(() => expect(FakeEventSource.latest).not.toBeNull())
  FakeEventSource.latest?.emit('terminal', {
    sequence: 1,
    kind: 'terminal',
    payload: { status: 'completed_with_errors', failed_items: 1 },
  })

  expect(await screen.findByText('Analyse beendet – 1 Titel fehlgeschlagen')).toBeVisible()
})

test('shows live progress for the active analysis', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }),
  )
  await userEvent.click(screen.getByRole('button', { name: '2 Titel analysieren' }))
  await waitFor(() => expect(FakeEventSource.latest).not.toBeNull())
  FakeEventSource.latest?.emit('progress', {
    sequence: 1,
    kind: 'progress',
    payload: { total_items: 2, completed_items: 1, failed_items: 0 },
  })

  expect(await screen.findByText('1 von 2 verarbeitet')).toBeVisible()
  expect(screen.getByRole('progressbar', { name: 'Analysefortschritt' })).toHaveAttribute(
    'aria-valuenow',
    '50',
  )
})

test('recovers terminal analysis state after the event stream disconnects', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }),
  )
  await userEvent.click(screen.getByRole('button', { name: '2 Titel analysieren' }))
  await waitFor(() => expect(FakeEventSource.latest).not.toBeNull())
  FakeEventSource.latest?.emit('error', {})

  expect(await screen.findByText('Analyse abgeschlossen')).toBeVisible()
})

test('select all analyzes every scanned track', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }),
  )
  expect(
    screen.getByText((_, element) =>
      element?.tagName === 'SPAN' && element.textContent === '2 von 2 ausgewählt'),
  ).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: '2 Titel analysieren' }))

  await waitFor(() => expect(analysisBodies).toEqual([{ track_ids: [11, 12] }]))
})

test('uses server-side missing-tag filters and clears analysis selection on changes', async () => {
  render(<WorkbenchView />)

  await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' })
  await userEvent.click(screen.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }))
  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))

  await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' })
  expect(screen.getByRole('button', { name: 'Auswahl analysieren' })).toBeDisabled()

  await userEvent.click(screen.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }))
  await userEvent.click(screen.getByRole('button', { name: 'Ohne Mood' }))

  await screen.findByRole('checkbox', { name: 'Library/two.mp3 analysieren' })
  expect(screen.getByRole('button', { name: 'Auswahl analysieren' })).toBeDisabled()
  const combinedFilterUrl = libraryRequestUrls.at(-1) ?? ''
  expect(combinedFilterUrl).toContain('missing_genre=true')
  expect(combinedFilterUrl).toContain('missing_mood=true')

  await userEvent.click(screen.getByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }))
  await userEvent.click(screen.getByRole('button', { name: '1 Titel analysieren' }))

  await waitFor(() => expect(analysisBodies).toEqual([{ track_ids: [12] }]))
})

test('withholds stale library rows while the next quick-filter query fails', async () => {
  render(<WorkbenchView />)
  await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' })
  const failedResponse = deferredResponse()
  nextLibraryResponse = failedResponse.promise

  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))

  expect(screen.queryByRole('checkbox', { name: 'Library/one.flac analysieren' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Auswahl analysieren' })).toBeDisabled()
  failedResponse.reject(new Error('network unreachable'))

  expect(await screen.findByText('Bibliothek konnte nicht geladen werden.')).toBeVisible()
  expect(screen.queryByRole('checkbox', { name: 'Library/one.flac analysieren' })).not.toBeInTheDocument()
})

test('shows a filter-specific empty state after success and no empty state after a load error', async () => {
  render(<WorkbenchView />)
  await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' })
  const failedResponse = deferredResponse()
  nextLibraryResponse = failedResponse.promise

  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))
  failedResponse.reject(new Error('network unreachable'))

  expect(await screen.findByText('Bibliothek konnte nicht geladen werden.')).toBeVisible()
  expect(screen.queryByText('Noch keine Titel gefunden. Starte zuerst einen Scan.')).not.toBeInTheDocument()

  nextLibraryResponse = Promise.resolve(Response.json({ items: [], total: 0, page: 1, page_size: 200 }))
  await userEvent.click(screen.getByRole('button', { name: 'Ohne Mood' }))

  expect(await screen.findByText('Keine Titel für diesen Filter gefunden.')).toBeVisible()
  expect(screen.queryByText('Bibliothek konnte nicht geladen werden.')).not.toBeInTheDocument()
})

test('selects every server-filtered track across two library pages', async () => {
  useMultiPageLibrary = true
  render(<WorkbenchView />)
  await screen.findByRole('checkbox', { name: 'Library/201.flac analysieren' })

  await userEvent.click(screen.getByRole('button', { name: 'Ohne Genre' }))
  await waitFor(() => expect(libraryRequestUrls.filter((url) => url.includes('missing_genre=true'))).toHaveLength(2))
  const filteredRequestUrls = libraryRequestUrls.filter((url) => url.includes('missing_genre=true'))
  for (const url of filteredRequestUrls) {
    const parameters = new URL(url, 'http://localhost').searchParams
    expect(parameters.get('missing_genre')).toBe('true')
    expect(parameters.get('missing_mood')).toBeNull()
  }

  await userEvent.click(await screen.findByRole('checkbox', { name: 'Alle gescannten Titel analysieren' }))
  expect(screen.getByText((_, element) => (
    element?.tagName === 'SPAN' && element.textContent === '201 von 201 ausgewählt'
  ))).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: '201 Titel analysieren' }))

  await waitFor(() => expect(analysisBodies).toEqual([{
    track_ids: Array.from({ length: 201 }, (_, index) => index + 1),
  }]))
})

test('hides written tracks by default and keeps file paths in a configurable column', async () => {
  includeWrittenTrack = true
  render(<WorkbenchView />)

  const libraryRow = (await screen.findByRole('checkbox', {
    name: 'Library/one.flac analysieren',
  })).closest('tr')
  expect(libraryRow).not.toBeNull()
  expect(screen.queryByText('Already Written')).not.toBeInTheDocument()
  const titleCell = libraryRow?.querySelector('.track-title')?.closest('td')
  const libraryTable = libraryRow?.closest('table')
  expect(libraryTable).not.toBeNull()
  expect(titleCell).not.toHaveTextContent('Library/one.flac')
  expect(within(libraryTable as HTMLTableElement).getByRole('columnheader', { name: 'Datei' })).toBeVisible()

  await userEvent.click(screen.getByText('Filter'))
  await userEvent.click(screen.getByLabelText('Vollständig geschriebene anzeigen'))
  expect(await screen.findByText('Already Written')).toBeVisible()

  await userEvent.click(screen.getByText('Spalten'))
  await userEvent.click(screen.getByLabelText('Spalte Datei anzeigen'))
  expect(within(libraryTable as HTMLTableElement).queryByRole('columnheader', { name: 'Datei' })).not.toBeInTheDocument()
})

test('keeps only one table settings menu open at a time', async () => {
  render(<WorkbenchView />)
  await screen.findByRole('checkbox', { name: 'Library/one.flac analysieren' })

  const filterSummary = screen.getByText('Filter')
  const columnSummary = screen.getByText('Spalten')
  const filterDetails = filterSummary.closest('details')
  const columnDetails = columnSummary.closest('details')

  await userEvent.click(filterSummary)
  expect(filterDetails).toHaveAttribute('open')
  await userEvent.click(columnSummary)
  expect(filterDetails).not.toHaveAttribute('open')
  expect(columnDetails).toHaveAttribute('open')
})

test('reports the number of tracks after a completed scan', async () => {
  render(<WorkbenchView />)

  await userEvent.click(screen.getByRole('button', { name: 'Bibliothek scannen' }))
  await waitFor(() => expect(FakeEventSource.latest).not.toBeNull())
  FakeEventSource.latest?.emit('terminal', {
    sequence: 1,
    kind: 'terminal',
    payload: { status: 'completed' },
  })

  expect(await screen.findByText('Scan abgeschlossen – 2 Titel gefunden')).toBeVisible()
})

test('write preview starts an observable job only after explicit confirmation', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Alle gefilterten Titel auswählen' }),
  )
  await userEvent.click(await screen.findByRole('button', { name: '63 Titel schreiben' }))

  expect(await screen.findByRole('dialog', { name: 'Tag-Änderungen schreiben' })).toBeVisible()
  expect(writeCalls).toBe(0)
  await userEvent.click(screen.getByRole('button', { name: 'Schreiben bestätigen' }))
  await waitFor(() => expect(FakeEventSource.latest).not.toBeNull())
  FakeEventSource.latest?.emit('progress', {
    sequence: 1,
    kind: 'progress',
    payload: { total_items: 1, completed_items: 1, failed_items: 0 },
  })
  expect(await screen.findByText('1 von 1 verarbeitet')).toBeVisible()
  FakeEventSource.latest?.emit('terminal', {
    sequence: 2,
    kind: 'terminal',
    payload: { total_items: 1, completed_items: 1, failed_items: 0, status: 'completed' },
  })
  expect(await screen.findByText('1 verifiziert')).toBeVisible()
  await waitFor(() => expect(
    screen.queryByRole('checkbox', { name: 'Library/one.flac analysieren' }),
  ).not.toBeInTheDocument())
  expect(writeCalls).toBe(1)
})

function resultRow(name: string) {
  return {
    id: name,
    track_id: name === 'one' ? 1 : 2,
    relative_path: `Artist/${name}.flac`,
    artist: name === 'one' ? 'Bastille' : 'Underworld',
    title: name === 'one' ? 'Quarter Past Midnight' : 'Rez',
    album: name === 'one' ? 'Doom Days' : 'Everything, Everything',
    duration_seconds: 180,
    metadata_source: 'embedded',
    processing_state: 'current',
    genres: [{ label: 'Electronic---House', confidence: 0.9, accepted: true }],
    moods: [{ label: 'moodtheme---happy', confidence: 0.8, accepted: true }],
    draft: {
      genres: ['Electronic; House', ...(ambientAdded ? ['Ambient'] : [])],
      moods: ['Happy'],
      selected: selectedCount > 0,
      dirty: ambientAdded,
    },
  }
}

test('select all targets the filtered result set and manual genres remain editable', async () => {
  render(<WorkbenchView />)

  await userEvent.type(await screen.findByLabelText('Ergebnisse filtern'), 'happy')
  await userEvent.click(
    screen.getByRole('checkbox', { name: 'Alle gefilterten Titel auswählen' }),
  )

  expect(await screen.findByText('63 Titel ausgewählt')).toBeInTheDocument()
  await userEvent.click(
    screen.getByRole('button', { name: 'Genre zu ausgewählten Titeln hinzufügen' }),
  )
  await userEvent.type(screen.getByLabelText('Genre'), 'Ambient{enter}')

  expect(await screen.findAllByText('Ambient')).toHaveLength(2)
})
