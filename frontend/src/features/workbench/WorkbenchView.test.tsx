import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { WorkbenchView } from './WorkbenchView'

let selectedCount = 0
let ambientAdded = false
let writeCalls = 0

beforeEach(() => {
  selectedCount = 0
  ambientAdded = false
  writeCalls = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
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

test('write preview never writes before explicit confirmation', async () => {
  render(<WorkbenchView />)

  await userEvent.click(
    await screen.findByRole('checkbox', { name: 'Alle gefilterten Titel auswählen' }),
  )
  await userEvent.click(await screen.findByRole('button', { name: '63 Titel schreiben' }))

  expect(await screen.findByRole('dialog', { name: 'Tag-Änderungen schreiben' })).toBeVisible()
  expect(writeCalls).toBe(0)
  await userEvent.click(screen.getByRole('button', { name: 'Schreiben bestätigen' }))
  expect(await screen.findByText('1 verifiziert')).toBeVisible()
  expect(writeCalls).toBe(1)
})

function resultRow(name: string) {
  return {
    id: name,
    track_id: name === 'one' ? 1 : 2,
    relative_path: `Artist/${name}.flac`,
    genres: [{ label: 'Electronic---House', confidence: 0.9 }],
    moods: [{ label: 'moodtheme---happy', confidence: 0.8 }],
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
