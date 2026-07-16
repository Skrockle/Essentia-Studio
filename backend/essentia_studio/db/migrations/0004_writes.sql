CREATE TABLE write_operations (
  id TEXT PRIMARY KEY,
  result_id TEXT NOT NULL REFERENCES analysis_results(id),
  relative_path TEXT NOT NULL,
  status TEXT NOT NULL,
  original_snapshot TEXT,
  post_write_size INTEGER,
  post_write_mtime_ns INTEGER,
  error_code TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- migrate:split
CREATE INDEX write_operations_created_idx
ON write_operations(created_at DESC, id DESC);
