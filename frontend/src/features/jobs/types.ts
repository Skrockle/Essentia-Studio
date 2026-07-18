export interface JobRecord {
  id: string
  type: 'scan' | 'analysis' | 'write' | 'undo' | 'playlist_write'
  status: string
  total_items: number
  completed_items: number
  failed_items: number
  cancel_requested?: boolean
}

export interface JobProgress {
  completed_items: number
  total_items: number
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
