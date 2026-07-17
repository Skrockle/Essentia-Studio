export interface JobRecord {
  id: string
  type: 'scan' | 'analysis' | 'write' | 'undo' | 'playlist_write' | 'benchmark'
  status: string
  total_items: number
  completed_items: number
  failed_items: number
}

export interface JobItemRecord {
  id: number
  job_id: string
  position: number
  value: string
  status: string
  result: Record<string, unknown> | null
  error: string | null
  error_code: string | null
}

export interface WriteOperation {
  id: string
  result_id: string
  relative_path: string
  status: string
  error_code: string | null
  error_message: string | null
  undo_available: boolean
}
