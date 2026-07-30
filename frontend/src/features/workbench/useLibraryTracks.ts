import { useCallback, useEffect, useRef, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { LibraryQuery, LibraryTrack, LibraryTrackPage } from './types'

const pageSize = 200

interface QueryBoundTracks {
  queryKey: string
  tracks: LibraryTrack[]
  error: string | null
  isLoading: boolean
}

function libraryQueryKey(query: LibraryQuery): string {
  return JSON.stringify([query.search, query.missingGenre, query.missingMood])
}

function isAbortedRequest(reason: unknown): boolean {
  return reason instanceof DOMException && reason.name === 'AbortError'
}

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
  const [libraryState, setLibraryState] = useState<QueryBoundTracks | null>(null)
  const requestSequence = useRef(0)
  const queryKey = libraryQueryKey(query)

  const refresh = useCallback(async () => {
    const requestId = requestSequence.current + 1
    requestSequence.current = requestId
    setLibraryState({ queryKey, tracks: [], error: null, isLoading: true })

    try {
      const tracks = await loadAllTracks(query)
      if (requestId !== requestSequence.current) return []
      setLibraryState({ queryKey, tracks, error: null, isLoading: false })
      return tracks
    } catch (reason: unknown) {
      if (requestId !== requestSequence.current || isAbortedRequest(reason)) return []
      setLibraryState({
        queryKey,
        tracks: [],
        error: 'Bibliothek konnte nicht geladen werden.',
        isLoading: false,
      })
      throw reason
    }
  }, [query, queryKey])

  useEffect(() => {
    const controller = new AbortController()
    const requestId = requestSequence.current + 1
    requestSequence.current = requestId
    loadAllTracks(query, controller.signal)
      .then((tracks) => {
        if (requestId !== requestSequence.current) return
        setLibraryState({ queryKey, tracks, error: null, isLoading: false })
      })
      .catch((reason: unknown) => {
        if (requestId !== requestSequence.current || isAbortedRequest(reason)) return
        setLibraryState({
          queryKey,
          tracks: [],
          error: 'Bibliothek konnte nicht geladen werden.',
          isLoading: false,
        })
      })
    return () => {
      controller.abort()
      requestSequence.current += 1
    }
  }, [query, queryKey])

  const isCurrentQuery = libraryState?.queryKey === queryKey

  return {
    tracks: isCurrentQuery ? libraryState.tracks : [],
    error: isCurrentQuery ? libraryState.error : null,
    isLoading: !isCurrentQuery || libraryState.isLoading,
    refresh,
  }
}
