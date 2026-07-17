import { useEffect, useState } from 'react'

import { apiRequest } from '../../api/client'
import type { TagOptions } from '../../api/types'

const emptyTagOptions: TagOptions = { genres: [], moods: [] }
const unavailableMessage = 'Tag-Vorschläge konnten nicht geladen werden. Freie Eingaben sind weiterhin möglich.'

export function useTagOptions() {
  const [options, setOptions] = useState<TagOptions>(emptyTagOptions)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    apiRequest<TagOptions>('/api/tag-options')
      .then((tagOptions) => {
        if (active) setOptions(tagOptions)
      })
      .catch(() => {
        if (!active) return
        setOptions(emptyTagOptions)
        setError(unavailableMessage)
      })

    return () => {
      active = false
    }
  }, [])

  return { options, error }
}
