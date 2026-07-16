import { render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { JobsView } from './JobsView'

const close = vi.fn()

class MockEventSource {
  close = close
  addEventListener = vi.fn()

  constructor(url: string) {
    void url
  }
}

beforeEach(() => {
  close.mockClear()
  vi.stubGlobal('EventSource', MockEventSource)
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/jobs')) {
        return Response.json([
          {
            id: 'job-1',
            type: 'analysis',
            status: 'running',
            total_items: 2,
            completed_items: 1,
            failed_items: 0,
          },
        ])
      }
      return Response.json([
        {
          id: 'write-1',
          result_id: 'result-1',
          relative_path: 'Artist/song.flac',
          status: 'verified',
          error_code: null,
          error_message: null,
          undo_available: true,
        },
      ])
    }),
  )
})

test('closes the event stream on unmount and exposes verified undo', async () => {
  const { unmount } = render(<JobsView />)

  expect(await screen.findByRole('button', { name: 'Tags wiederherstellen' })).toBeEnabled()
  unmount()
  expect(close).toHaveBeenCalledOnce()
})
