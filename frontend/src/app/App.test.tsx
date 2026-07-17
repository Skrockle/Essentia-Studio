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
      if (url.includes('/api/results')) {
        return Response.json({
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
          selected_count: 0,
        })
      }
      if (url.endsWith('/api/automation/status')) {
        return Response.json({
          enabled: false,
          trigger_mode: 'disabled',
          watcher_health: 'disabled',
          next_runs: [],
          last_run: null,
          last_error: null,
        })
      }
      return Response.json({
        values: {
          analysis: {
            workers: 1,
            max_audio_seconds: 300,
            genre_threshold: 0.15,
            mood_threshold: 0.005,
            genre_count: 3,
            write_confidence_tags: true,
            overwrite_existing: false,
            compute: 'auto',
          },
          automation: {
            enabled: false,
            watcher: false,
            schedule: '0 * * * *',
            timezone: 'UTC',
            mode: 'analyze',
            quiet_seconds: 30,
          },
          benchmark: { minimum_track_seconds: 60, safety_margin_percent: 30 },
        },
        sources: {
          'analysis.workers': 'env',
        },
      })
    }),
  )
})

test('opens settings and explains the active CPU image', async () => {
  render(<App />)

  await userEvent.click(screen.getByRole('button', { name: 'Einstellungen' }))

  expect(await screen.findByText('CPU-Image')).toBeInTheDocument()
  expect(screen.getByText('/music')).toBeInTheDocument()
  expect(screen.getByLabelText('Worker')).toBeDisabled()
  expect(screen.getByText('Durch Umgebungsvariable festgelegt')).toBeVisible()
})

test('persists a dark theme selection and applies it to the document', async () => {
  render(<App />)

  await userEvent.selectOptions(screen.getByLabelText('Farbschema'), 'dark')

  expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  expect(localStorage.getItem('essentia-studio.theme.v1')).toBe('dark')
})
