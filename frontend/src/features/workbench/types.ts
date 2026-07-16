export interface Prediction {
  label: string
  confidence: number
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
  genres: Prediction[]
  moods: Prediction[]
  draft: Draft
}

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
}

export interface LibraryTrackPage {
  items: LibraryTrack[]
  total: number
  page: number
  page_size: number
}
