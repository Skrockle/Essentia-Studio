import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { PlaylistsView } from './PlaylistsView'

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/catalog')) {
        return Response.json({
          fields: [
            { key: 'title', label: 'Title', type: 'string', category: 'Core' },
            { key: 'rating', label: 'Rating', type: 'number', category: 'Playback' },
          ],
          operators: {
            string: [{ key: 'is', label: 'Ist genau' }],
            number: [
              { key: 'is', label: 'Ist genau' },
              { key: 'gt', label: 'Ist größer als' },
            ],
          },
          sort_options: [],
          presets: [],
          this_is_methods: [{ id: 'greatest_hits', label: 'Greatest hits' }],
        })
      }
      return Response.json([])
    }),
  )
})

test('builds a nested any group with field-specific controls', async () => {
  render(<PlaylistsView />)
  await userEvent.click(await screen.findByRole('tab', { name: 'Eigene Regeln' }))
  await userEvent.click(screen.getByRole('button', { name: 'ODER-Gruppe hinzufügen' }))
  await userEvent.selectOptions(screen.getAllByLabelText('Feld')[0], 'rating')

  expect(screen.getAllByLabelText('Operator')[0]).toHaveTextContent('Ist größer als')
  expect(screen.getAllByLabelText('Wert')[0]).toHaveAttribute('type', 'number')
})
