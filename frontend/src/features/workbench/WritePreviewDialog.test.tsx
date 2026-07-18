import { expect, test, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

import { ApiError } from '../../api/client'
import { WritePreviewDialog } from './WritePreviewDialog'

test('shows a readable error when a selected audio file cannot be previewed', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      throw new ApiError(
        'invalid_audio_file',
        'Die Datei ist beschädigt oder kein gültiges Audioformat und kann nicht gelesen werden.',
        {},
      )
    }),
  )

  render(
    <WritePreviewDialog
      onClose={() => undefined}
      onCompleted={() => undefined}
      selection={{ mode: 'ids', ids: ['result-1'] }}
    />,
  )

  expect(await screen.findByText(/beschädigt oder kein gültiges Audioformat/)).toBeVisible()
})
