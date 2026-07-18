import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, test, vi } from 'vitest'

import { useTagOptions } from './useTagOptions'

describe('useTagOptions', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  test('stores the catalog returned by the API', async () => {
    vi.mocked(fetch).mockResolvedValue(
      Response.json({ genres: ['Ambient', 'Electronic'], moods: ['Calm'] }),
    )

    const { result } = renderHook(() => useTagOptions())

    await waitFor(() => expect(result.current.options).toEqual({
      genres: ['Ambient', 'Electronic'],
      moods: ['Calm'],
    }))
    expect(result.current.error).toBeNull()
    expect(fetch).toHaveBeenCalledWith('/api/tag-options', {
      headers: { 'Content-Type': 'application/json' },
    })
  })

  test('keeps free entries available when catalog loading fails', async () => {
    vi.mocked(fetch).mockResolvedValue(
      Response.json(
        { error: { code: 'tag_options_unavailable', message: 'Katalog nicht verfügbar' } },
        { status: 503 },
      ),
    )

    const { result } = renderHook(() => useTagOptions())

    await waitFor(() => expect(result.current.error).toBe(
      'Tag-Vorschläge konnten nicht geladen werden. Freie Eingaben sind weiterhin möglich.',
    ))
    expect(result.current.options).toEqual({ genres: [], moods: [] })
  })
})
