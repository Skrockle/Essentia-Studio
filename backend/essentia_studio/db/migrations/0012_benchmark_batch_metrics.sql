CREATE TABLE benchmark_measurements_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES benchmark_runs(id) ON DELETE CASCADE,
  compute TEXT NOT NULL CHECK (compute IN ('cpu', 'cuda')),
  batch_size INTEGER NOT NULL DEFAULT 1 CHECK (batch_size IN (1, 2, 4, 8)),
  initialization_seconds REAL NOT NULL,
  warmup_seconds REAL NOT NULL,
  measured_seconds_json TEXT NOT NULL,
  baseline_peak_bytes INTEGER NOT NULL,
  worker_peak_bytes INTEGER NOT NULL,
  model_ids_json TEXT NOT NULL,
  cuda_oom_fallbacks INTEGER NOT NULL DEFAULT 0,
  UNIQUE(run_id, compute, batch_size)
);
-- migrate:split

INSERT INTO benchmark_measurements_v2 (
  id, run_id, compute, batch_size, initialization_seconds, warmup_seconds,
  measured_seconds_json, baseline_peak_bytes, worker_peak_bytes, model_ids_json,
  cuda_oom_fallbacks
)
SELECT id, run_id, compute, 1, initialization_seconds, warmup_seconds,
  measured_seconds_json, baseline_peak_bytes, worker_peak_bytes, model_ids_json, 0
FROM benchmark_measurements;
-- migrate:split

DROP TABLE benchmark_measurements;
-- migrate:split

ALTER TABLE benchmark_measurements_v2 RENAME TO benchmark_measurements;
