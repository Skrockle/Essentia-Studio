import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import { useLibraryTracks } from './useLibraryTracks'
import type { LibraryQuery } from './types'

const noMissingTags: LibraryQuery = { search: '', missingGenre: false, missingMood: false }

function libraryTrack(id: number) {
  return {
    id,
    relative_path: `Library/${id}.flac`,
    extension: '.flac',
    size: 1024,
    mtime_ns: id,
    last_seen: '2026-07-30T00:00:00Z',
    present: true,
    artist: 'Artist',
    title: `Track ${id}`,
    album: 'Album',
    duration_seconds: 180,
    metadata_source: 'embedded' as const,
    processing_state: 'new' as const,
  }
}

function libraryPage(ids: number[], total = ids.length) {
  return Response.json({ items: ids.map(libraryTrack), total, page: 1, page_size: 200 })
}

function deferredResponse() {
  let resolve: (response: Response) => void
  let reject: (reason: unknown) => void
  const promise = new Promise<Response>((nextResolve, nextReject) => {
    resolve = nextResolve
    reject = nextReject
  })
  return { promise, resolve: resolve!, reject: reject! }
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

test.each([
  [{ ...noMissingTags, missingGenre: true }, '/api/library/tracks?page=1&page_size=200&missing_genre=true'],
  [{ ...noMissingTags, missingMood: true }, '/api/library/tracks?page=1&page_size=200&missing_mood=true'],
  [{ ...noMissingTags, missingGenre: true, missingMood: true }, '/api/library/tracks?page=1&page_size=200&missing_genre=true&missing_mood=true'],
  [{ search: 'Night Drive', missingGenre: true, missingMood: true }, '/api/library/tracks?page=1&page_size=200&search=Night+Drive&missing_genre=true&missing_mood=true'],
])('loads the exact server query %o', async (query: LibraryQuery, expectedUrl: string) => {
  const requestUrls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    requestUrls.push(String(input))
    return libraryPage([1])
  }))

  const { result } = renderHook(() => useLibraryTracks(query))

  await waitFor(() => expect(result.current.isLoading).toBe(false))
  expect(requestUrls).toEqual([expectedUrl])
})

test('keeps query parameters and resets paging when the query changes', async () => {
  const requestUrls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    requestUrls.push(url)
    const page = new URL(url, 'http://localhost').searchParams.get('page')
    const pageIds = page === '1'
      ? Array.from({ length: 200 }, (_, index) => index + 1)
      : [201]
    return libraryPage(pageIds, 201)
  }))
  const initialQuery = { search: 'first', missingGenre: true, missingMood: false }
  const nextQuery = { search: 'second', missingGenre: false, missingMood: true }
  const { result, rerender } = renderHook(({ query }) => useLibraryTracks(query), {
    initialProps: { query: initialQuery },
  })

  await waitFor(() => expect(result.current.isLoading).toBe(false))
  expect(result.current.tracks.map((track) => track.id)).toEqual(
    Array.from({ length: 201 }, (_, index) => index + 1),
  )
  rerender({ query: nextQuery })
  await waitFor(() => expect(result.current.isLoading).toBe(false))

  expect(requestUrls).toEqual([
    '/api/library/tracks?page=1&page_size=200&search=first&missing_genre=true',
    '/api/library/tracks?page=2&page_size=200&search=first&missing_genre=true',
    '/api/library/tracks?page=1&page_size=200&search=second&missing_mood=true',
    '/api/library/tracks?page=2&page_size=200&search=second&missing_mood=true',
  ])
})

test('withholds stale tracks and reports a German error for the current failed query', async () => {
  const initialResponse = deferredResponse()
  const failedResponse = deferredResponse()
  let requestCount = 0
  vi.stubGlobal('fetch', vi.fn(() => {
    requestCount += 1
    return requestCount === 1 ? initialResponse.promise : failedResponse.promise
  }))
  const { result, rerender } = renderHook(({ query }) => useLibraryTracks(query), {
    initialProps: { query: noMissingTags },
  })

  initialResponse.resolve(libraryPage([1]))
  await waitFor(() => expect(result.current.tracks.map((track) => track.id)).toEqual([1]))
  rerender({ query: { ...noMissingTags, missingGenre: true } })

  expect(result.current.tracks).toEqual([])
  expect(result.current.isLoading).toBe(true)
  failedResponse.reject(new Error('network unreachable'))

  await waitFor(() => expect(result.current.error).toBe('Bibliothek konnte nicht geladen werden.'))
  expect(result.current.tracks).toEqual([])
})

test('ignores an older response after a newer query has loaded', async () => {
  const olderResponse = deferredResponse()
  const newerResponse = deferredResponse()
  let requestCount = 0
  vi.stubGlobal('fetch', vi.fn(() => {
    requestCount += 1
    return requestCount === 1 ? olderResponse.promise : newerResponse.promise
  }))
  const { result, rerender } = renderHook(({ query }) => useLibraryTracks(query), {
    initialProps: { query: noMissingTags },
  })

  await waitFor(() => expect(requestCount).toBe(1))
  rerender({ query: { ...noMissingTags, missingMood: true } })
  await waitFor(() => expect(requestCount).toBe(2))
  newerResponse.resolve(libraryPage([2]))
  await waitFor(() => expect(result.current.tracks.map((track) => track.id)).toEqual([2]))
  await act(async () => {
    olderResponse.resolve(libraryPage([1]))
    await Promise.resolve()
  })

  expect(result.current.tracks.map((track) => track.id)).toEqual([2])
})
