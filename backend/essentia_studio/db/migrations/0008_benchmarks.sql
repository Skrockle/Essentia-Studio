CREATE TABLE benchmark_runs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
  sample_track_id INTEGER REFERENCES library_tracks(id) ON DELETE SET NULL,
  sample_relative_path TEXT,
  sample_seconds REAL NOT NULL,
  snapshot_json TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL,
  recommended_workers INTEGER,
  error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT
);
-- migrate:split

CREATE INDEX benchmark_runs_snapshot_idx
ON benchmark_runs(snapshot_hash, created_at DESC);
-- migrate:split

CREATE TABLE benchmark_measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES benchmark_runs(id) ON DELETE CASCADE,
  compute TEXT NOT NULL CHECK (compute IN ('cpu', 'cuda')),
  initialization_seconds REAL NOT NULL,
  warmup_seconds REAL NOT NULL,
  measured_seconds_json TEXT NOT NULL,
  baseline_peak_bytes INTEGER NOT NULL,
  worker_peak_bytes INTEGER NOT NULL,
  model_ids_json TEXT NOT NULL,
  UNIQUE(run_id, compute)
);
