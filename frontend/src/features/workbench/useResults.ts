import { useCallback, useEffect, useMemo, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { ResultPage, ResultQuery, ResultRow, SelectionSpec } from './types'

const emptyPage: ResultPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
  selected_count: 0,
}

export function useResults(query: ResultQuery) {
  const [page, setPage] = useState(emptyPage)
  const [error, setError] = useState<string | null>(null)
  const [selection, setSelection] = useState<SelectionSpec>({ mode: 'ids', ids: [] })
  const [refreshVersion, setRefreshVersion] = useState(0)
  const refresh = useCallback(() => setRefreshVersion((version) => version + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    const parameters = new URLSearchParams()
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') parameters.set(key, String(value))
    })

    apiRequest<ResultPage>(`/api/results?${parameters}`, { signal: controller.signal })
      .then((nextPage) => {
        setError(null)
        setPage(nextPage)
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setError(error instanceof Error ? error.message : 'Ergebnisse konnten nicht geladen werden.')
        }
      })

    return () => controller.abort()
  }, [query, refreshVersion])

  async function selectAll(selected: boolean) {
    const nextSelection: SelectionSpec = selected
      ? { mode: 'query', query, excluded_ids: [] }
      : { mode: 'ids', ids: [] }
    setSelection(nextSelection)
    setPage((current) => ({
      ...current,
      selected_count: selected ? current.total : 0,
      items: current.items.map((row) => ({
        ...row,
        draft: { ...row.draft, selected },
      })),
    }))
    await apiRequest('/api/results/selection', {
      method: 'POST',
      body: JSON.stringify({ selection: nextSelection, selected }),
    })
    refresh()
  }

  async function selectRow(row: ResultRow, selected: boolean) {
    setPage((current) => ({
      ...current,
      selected_count: Math.max(0, current.selected_count + (selected ? 1 : -1)),
      items: current.items.map((item) =>
        item.id === row.id ? { ...item, draft: { ...item.draft, selected } } : item,
      ),
    }))
    await apiRequest('/api/results/selection', {
      method: 'POST',
      body: JSON.stringify({ selection: { mode: 'ids', ids: [row.id] }, selected }),
    })
    if (selection.mode === 'query' && !selected) {
      setSelection({
        ...selection,
        excluded_ids: [...selection.excluded_ids, row.id],
      })
    } else if (selection.mode === 'ids') {
      setSelection({
        mode: 'ids',
        ids: selected
          ? [...new Set([...selection.ids, row.id])]
          : selection.ids.filter((id) => id !== row.id),
      })
    }
    refresh()
  }

  async function saveDraft(row: ResultRow, genres: string[], moods: string[]) {
    await apiRequest(`/api/results/${row.id}/draft`, {
      method: 'PATCH',
      body: JSON.stringify({ genres, moods }),
    })
    refresh()
  }

  async function bulkUpdate(operation: string, value: string) {
    const effectiveSelection: SelectionSpec =
      selection.mode === 'ids' && selection.ids.length === 0
        ? { mode: 'ids', ids: page.items.filter((row) => row.draft.selected).map((row) => row.id) }
        : selection
    await apiRequest('/api/results/bulk-draft', {
      method: 'POST',
      body: JSON.stringify({ selection: effectiveSelection, operation, value }),
    })
    refresh()
  }

  const effectiveSelection = useMemo<SelectionSpec>(() => {
    if (selection.mode !== 'ids' || selection.ids.length > 0 || page.selected_count === 0) {
      return selection
    }
    return {
      mode: 'ids',
      ids: page.items.filter((row) => row.draft.selected).map((row) => row.id),
    }
  }, [page.items, page.selected_count, selection])

  return {
    page,
    error,
    selection: effectiveSelection,
    refresh,
    selectAll,
    selectRow,
    saveDraft,
    bulkUpdate,
  }
}
