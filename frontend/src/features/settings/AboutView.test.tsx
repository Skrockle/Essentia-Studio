import { render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { AboutView } from './AboutView'

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/health')) {
        return Response.json({ status: 'ok', version: '1.2.3' })
      }
      return Response.json({ image_variant: 'cuda', available_compute: ['cpu', 'cuda'] })
    }),
  )
})

test('shows runtime, upstreams, and all relevant licenses', async () => {
  render(<AboutView />)

  expect(await screen.findByText('Version 1.2.3')).toBeInTheDocument()
  expect(screen.getByText(/cuda-Image/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Essentia-to-Metadata/ })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Navidrome-SmartPlaylist/ })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /MIT/ })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /AGPL-3.0/ })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /CC BY-NC-ND 4.0/ })).toBeInTheDocument()
  expect(screen.getByText(/nicht kommerziell genutzt/)).toBeInTheDocument()
})
