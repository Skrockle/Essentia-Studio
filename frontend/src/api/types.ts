export type ViewId = 'workbench' | 'playlists' | 'jobs' | 'settings' | 'about'

export type PathStatus = 'ready' | 'read_only' | 'missing'
export type ComputeMode = 'auto' | 'cpu' | 'cuda'

export interface PathCapability {
  path: string
  status: PathStatus
}

export interface ModelInfo {
  name: string
  [key: string]: string
}

export interface Capabilities {
  image_variant: 'cpu' | 'cuda'
  available_compute: Array<'cpu' | 'cuda'>
  music_root: PathCapability
  data_dir: PathCapability
  playlist_dir: PathCapability
  models: ModelInfo[]
}

export interface AppSettings {
  worker_count: number
  max_audio_seconds: number
  genre_threshold: number
  mood_threshold: number
  genre_count: number
  write_confidence_tags: boolean
  overwrite_existing: boolean
  compute_preference: ComputeMode
}
