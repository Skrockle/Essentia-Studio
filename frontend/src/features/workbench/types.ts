export interface Prediction {
  label: string
  confidence: number
  accepted: boolean
}

export interface Draft {
  genres: string[]
  moods: string[]
  selected: boolean
  dirty: boolean
}

export interface ResultRow {
  id: string
  track_id: number
  relative_path: string
  artist: string
  title: string
  album: string | null
  duration_seconds: number | null
  metadata_source: 'embedded' | 'filename' | 'directory' | 'fallback'
  processing_state: ProcessingState
  genres: Prediction[]
  moods: Prediction[]
  draft: Draft
}

export type ProcessingState = 'new' | 'current' | 'changed' | 'written' | 'failed'

export interface ResultQuery {
  search?: string
  genre?: string
  mood?: string
  status?: string
  selected?: boolean
}

export type SelectionSpec =
  | { mode: 'ids'; ids: string[] }
  | { mode: 'query'; query: ResultQuery; excluded_ids: string[] }

export interface ResultPage {
  items: ResultRow[]
  total: number
  page: number
  page_size: number
  selected_count: number
}

export interface LibraryTrack {
  id: number
  relative_path: string
  extension: string
  size: number
  mtime_ns: number
  last_seen: string
  present: boolean
  artist: string
  title: string
  album: string | null
  duration_seconds: number | null
  metadata_source: 'embedded' | 'filename' | 'directory' | 'fallback'
  processing_state: ProcessingState
}

export interface LibraryTrackPage {
  items: LibraryTrack[]
  total: number
  page: number
  page_size: number
}
