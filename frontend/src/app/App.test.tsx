import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { App } from './App'

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/capabilities')) {
        return new Response(
          JSON.stringify({
            image_variant: 'cpu',
            available_compute: ['cpu'],
            models: [],
            music_root: { path: '/music', status: 'ready' },
            data_dir: { path: '/data', status: 'ready' },
            playlist_dir: { path: '/music/SmartPlaylists', status: 'ready' },
          }),
        )
      }
      return new Response(
        JSON.stringify({
          worker_count: 1,
          max_audio_seconds: 300,
          genre_threshold: 0.15,
          mood_threshold: 0.005,
          genre_count: 3,
          write_confidence_tags: true,
          overwrite_existing: false,
          compute_preference: 'auto',
        }),
      )
    }),
  )
})

test('opens settings and explains the active CPU image', async () => {
  render(<App />)

  await userEvent.click(screen.getByRole('button', { name: 'Einstellungen' }))

  expect(await screen.findByText('CPU-Image')).toBeInTheDocument()
  expect(screen.getByText('/music')).toBeInTheDocument()
})
