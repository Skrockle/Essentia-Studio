CREATE TABLE analysis_results (
  id TEXT PRIMARY KEY,
  track_id INTEGER NOT NULL REFERENCES library_tracks(id),
  job_id TEXT REFERENCES jobs(id),
  raw_genres TEXT NOT NULL,
  raw_moods TEXT NOT NULL,
  model_ids TEXT NOT NULL,
  analyzed_size INTEGER NOT NULL,
  analyzed_mtime_ns INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- migrate:split
CREATE INDEX analysis_results_track_created_idx
ON analysis_results(track_id, created_at DESC, id DESC);
-- migrate:split
CREATE TABLE tag_drafts (
  result_id TEXT PRIMARY KEY REFERENCES analysis_results(id) ON DELETE CASCADE,
  genres TEXT NOT NULL,
  moods TEXT NOT NULL,
  selected INTEGER NOT NULL DEFAULT 0 CHECK (selected IN (0, 1)),
  dirty INTEGER NOT NULL DEFAULT 0 CHECK (dirty IN (0, 1)),
  status TEXT NOT NULL DEFAULT 'draft',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
