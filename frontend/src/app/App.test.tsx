import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import { App } from './App'

let includeCuda = false

beforeEach(() => {
  includeCuda = false
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/api/capabilities')) {
        return new Response(
          JSON.stringify({
            image_variant: includeCuda ? 'cuda' : 'cpu',
            available_compute: includeCuda ? ['cpu', 'cuda'] : ['cpu'],
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
            cpu_workers: 1,
            gpu_workers: 1,
            gpu_batch_size: 1,
            gpu_queue_size: 8,
            max_audio_seconds: 300,
            genre_threshold: 0.25,
            mood_threshold: 0.1,
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
          'analysis.cpu_workers': 'env',
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
  expect(screen.getByLabelText('CPU-Worker')).toBeDisabled()
  expect(screen.getByText('Durch Umgebungsvariable festgelegt')).toBeVisible()
  expect(screen.getByLabelText('Genre-Schwelle')).toHaveValue(25)
  expect(screen.getByLabelText('Mood-Schwelle')).toHaveValue(10)
  expect(screen.getByLabelText('Maximale Genres')).toHaveValue(3)
  await userEvent.hover(
    screen.getByRole('button', { name: 'Erklärung zu Maximale Genres' }),
  )
  expect(screen.getByRole('tooltip')).toHaveTextContent(
    'Die Schwelle kann zu weniger Vorschlägen führen',
  )
})

test('shows safe CUDA tuning controls in the CUDA image', async () => {
  includeCuda = true
  render(<App />)

  await userEvent.click(screen.getByRole('button', { name: 'Einstellungen' }))

  expect(await screen.findByText('GPU-Tuning')).toBeInTheDocument()
  expect(screen.getByLabelText('GPU-Worker')).toBeDisabled()
  expect(screen.getByLabelText('GPU-Batchgröße')).toHaveValue('1')
  expect(screen.getByLabelText('CUDA-Queue')).toHaveValue(8)
})

test('persists a dark theme selection and applies it to the document', async () => {
  render(<App />)

  await userEvent.selectOptions(screen.getByLabelText('Farbschema'), 'dark')

  expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  expect(localStorage.getItem('essentia-studio.theme.v1')).toBe('dark')
})
