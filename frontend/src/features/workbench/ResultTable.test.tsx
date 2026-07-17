import { render, screen, within } from '@testing-library/react'
import { describe, expect, test, vi } from 'vitest'

import { ResultTable } from './ResultTable'
import type { ResultRow } from './types'

function resultRow(overrides: Partial<ResultRow> = {}): ResultRow {
  return {
    id: 'result-1',
    track_id: 1,
    relative_path: 'testdateien/song.flac',
    artist: 'Test Artist',
    title: 'Test Song',
    album: 'Test Album',
    duration_seconds: 180,
    metadata_source: 'embedded',
    processing_state: 'current',
    genres: [],
    moods: [],
    draft: {
      genres: ['Ambient'],
      moods: ['Calm'],
      selected: false,
      dirty: false,
    },
    ...overrides,
  }
}

function renderTable(row: ResultRow) {
  render(
    <ResultTable
      allSelected={false}
      onSaveDraft={vi.fn()}
      onSelectAll={vi.fn()}
      onSelectRow={vi.fn()}
      rows={[row]}
      visibleColumns={['artist', 'title', 'file', 'genres', 'moods', 'status']}
    />,
  )
  return screen.getByRole('checkbox', { name: `${row.relative_path} auswählen` }).closest('tr')
}

describe('ResultTable status', () => {
  test('shows one canonical written status without a contradictory proposal', () => {
    const row = renderTable(resultRow({ processing_state: 'written' }))

    expect(row).not.toBeNull()
    expect(within(row as HTMLTableRowElement).getByText('Geschrieben')).toBeVisible()
    expect(within(row as HTMLTableRowElement).queryByText('Vorschlag')).not.toBeInTheDocument()
  })

  test('shows a manually changed draft as pending work', () => {
    const row = renderTable(resultRow({
      draft: {
        genres: ['Ambient', 'Downtempo'],
        moods: ['Calm'],
        selected: false,
        dirty: true,
      },
    }))

    expect(row).not.toBeNull()
    expect(within(row as HTMLTableRowElement).getByText('Bearbeitet')).toBeVisible()
    expect(within(row as HTMLTableRowElement).queryByText('Aktuell')).not.toBeInTheDocument()
  })
})
