import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'

import type { BenchmarkRun } from '../../api/types'
import { BenchmarkPanel } from './BenchmarkPanel'

const cpuResult: BenchmarkRun = {
  id: 'run-1',
  status: 'completed',
  sample_track_id: 7,
  sample_relative_path: 'Artist/Long Song.flac',
  sample_seconds: 60,
  snapshot: { memory_bytes: 4_294_967_296, cpu_count: 4 },
  recommended_workers: 2,
  error: null,
  created_at: '2026-07-17T10:00:00Z',
  finished_at: '2026-07-17T10:02:00Z',
  current: true,
  measurements: [{
    compute: 'cpu',
    initialization_seconds: 2,
    warmup_seconds: 1,
    measured_seconds: [10, 11, 9],
    average_seconds: 10,
    seconds_per_audio_minute: 10,
    baseline_peak_bytes: 500_000_000,
    worker_peak_bytes: 800_000_000,
    model_ids: ['genre-discogs400'],
  }],
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
})

test('shows a worker recommendation without applying it', async () => {
  const fetchMock = vi.mocked(fetch)
  fetchMock
    .mockResolvedValueOnce(Response.json([]))
    .mockResolvedValueOnce(Response.json([]))
    .mockResolvedValueOnce(Response.json({ id: 'job-1', status: 'queued' }))
    .mockResolvedValueOnce(Response.json([cpuResult]))
  render(<BenchmarkPanel onApplied={vi.fn()} />)

  await userEvent.click(await screen.findByRole('button', { name: 'Benchmark starten' }))

  expect(await screen.findByText('Empfohlen: 2 Worker')).toBeVisible()
  expect(fetchMock).not.toHaveBeenCalledWith(
    '/api/benchmarks/run-1/apply',
    expect.objectContaining({ method: 'POST' }),
  )
  expect(screen.getByText('Artist/Long Song.flac')).toBeVisible()
  expect(screen.queryByText(/CUDA .* schneller/)).not.toBeInTheDocument()
})

test('compares cuda and prevents applying a stale result', async () => {
  const cudaResult: BenchmarkRun = {
    ...cpuResult,
    current: false,
    measurements: [
      ...cpuResult.measurements,
      { ...cpuResult.measurements[0], compute: 'cuda', average_seconds: 4 },
    ],
  }
  vi.mocked(fetch)
    .mockResolvedValueOnce(Response.json([cudaResult]))
    .mockResolvedValueOnce(Response.json([]))
  render(<BenchmarkPanel onApplied={vi.fn()} />)

  expect(await screen.findByText('CUDA 2,5× schneller')).toBeVisible()
  expect(screen.getByRole('button', { name: '2 Worker übernehmen' })).toBeDisabled()
  expect(screen.getByText(/nicht mehr zur aktuellen Umgebung/)).toBeVisible()
})
