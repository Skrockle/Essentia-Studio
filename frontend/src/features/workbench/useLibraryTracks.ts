import { useCallback, useEffect, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { LibraryTrack, LibraryTrackPage } from './types'

const pageSize = 200

async function loadAllTracks(search: string, signal?: AbortSignal): Promise<LibraryTrack[]> {
  const tracks: LibraryTrack[] = []
  let page = 1

  while (true) {
    const parameters = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (search) parameters.set('search', search)

    const response = await apiRequest<LibraryTrackPage>(
      `/api/library/tracks?${parameters}`,
      { signal },
    )
    tracks.push(...response.items)
    if (tracks.length >= response.total || response.items.length === 0) return tracks
    page += 1
  }
}

export function useLibraryTracks(search: string) {
  const [tracks, setTracks] = useState<LibraryTrack[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const nextTracks = await loadAllTracks(search)
    setTracks(nextTracks)
    setError(null)
    return nextTracks
  }, [search])

  useEffect(() => {
    const controller = new AbortController()
    loadAllTracks(search, controller.signal)
      .then((nextTracks) => {
        setTracks(nextTracks)
        setError(null)
      })
      .catch((reason: unknown) => {
        if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
          setError(reason instanceof Error ? reason.message : 'Bibliothek konnte nicht geladen werden.')
        }
      })
    return () => controller.abort()
  }, [search])

  return { tracks, error, refresh }
}
