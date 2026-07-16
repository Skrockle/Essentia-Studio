import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { WorkbenchView } from './WorkbenchView'

let selectedCount = 0
let ambientAdded = false

beforeEach(() => {
  selectedCount = 0
  ambientAdded = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/api/results/selection')) {
        selectedCount = 63
        return Response.json({ affected: 63 })
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
