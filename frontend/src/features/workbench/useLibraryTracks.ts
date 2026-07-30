import { useCallback, useEffect, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { LibraryQuery, LibraryTrack, LibraryTrackPage } from './types'

const pageSize = 200

async function loadAllTracks(query: LibraryQuery, signal?: AbortSignal): Promise<LibraryTrack[]> {
  const tracks: LibraryTrack[] = []
  let page = 1

  while (true) {
    const parameters = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (query.search) parameters.set('search', query.search)
    if (query.missingGenre) parameters.set('missing_genre', 'true')
    if (query.missingMood) parameters.set('missing_mood', 'true')

    const response = await apiRequest<LibraryTrackPage>(
      `/api/library/tracks?${parameters}`,
      { signal },
    )
    tracks.push(...response.items)
    if (tracks.length >= response.total || response.items.length === 0) return tracks
    page += 1
  }
}

export function useLibraryTracks(query: LibraryQuery) {
  const [tracks, setTracks] = useState<LibraryTrack[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const nextTracks = await loadAllTracks(query)
    setTracks(nextTracks)
    setError(null)
    return nextTracks
  }, [query])

  useEffect(() => {
    const controller = new AbortController()
    loadAllTracks(query, controller.signal)
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
  }, [query])

  return { tracks, error, refresh }
}
