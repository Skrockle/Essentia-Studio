export type ViewId = 'workbench' | 'playlists' | 'jobs' | 'settings' | 'about'

export type PathStatus = 'ready' | 'read_only' | 'missing'
export type ComputeMode = 'auto' | 'cpu' | 'cuda'
export type SettingSource = 'default' | 'file' | 'env'

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

export interface HealthResponse {
  status: 'ok'
  version: string
}

export interface TagOptions {
  genres: string[]
  moods: string[]
}

export interface AppSettings {
  analysis: {
    workers: number
    cpu_workers: number
    gpu_workers: number
    gpu_batch_size: 1 | 2 | 4 | 8
    gpu_queue_size: number
    max_audio_seconds: number
    genre_threshold: number
    mood_threshold: number
    genre_count: number
    write_confidence_tags: boolean
    overwrite_existing: boolean
    compute: ComputeMode
  }
  automation: {
    enabled: boolean
    watcher: boolean
    schedule: string
    timezone: string
    mode: 'analyze' | 'analyze_and_write'
    quiet_seconds: number
  }
  benchmark: {
    minimum_track_seconds: number
    safety_margin_percent: number
  }
}

export interface EffectiveSettings {
  values: AppSettings
  sources: Record<string, SettingSource>
}

export interface AutomationStatus {
  enabled: boolean
  trigger_mode: 'disabled' | 'watcher' | 'schedule' | 'fallback_schedule'
  watcher_health: 'disabled' | 'starting' | 'ready' | 'failed'
  next_runs: string[]
  last_run: string | null
  last_error: string | null
}

export interface BenchmarkMeasurement {
  compute: 'cpu' | 'cuda'
  initialization_seconds: number
  warmup_seconds: number
  measured_seconds: number[]
  average_seconds: number
  seconds_per_audio_minute: number
  baseline_peak_bytes: number
  worker_peak_bytes: number
  model_ids: string[]
}

export interface BenchmarkRun {
  id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  sample_track_id: number | null
  sample_relative_path: string | null
  sample_seconds: number
  snapshot: Record<string, unknown>
  recommended_workers: number | null
  error: string | null
  created_at: string | null
  finished_at: string | null
  measurements: BenchmarkMeasurement[]
  current: boolean
}

export interface JobResponse {
  id: string
  type: string
  status: string
  configuration: Record<string, unknown>
  total_items: number
  completed_items: number
  failed_items: number
}
