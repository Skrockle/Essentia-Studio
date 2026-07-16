CREATE TABLE library_tracks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  relative_path TEXT NOT NULL UNIQUE,
  extension TEXT NOT NULL,
  size INTEGER NOT NULL CHECK (size >= 0),
  mtime_ns INTEGER NOT NULL CHECK (mtime_ns >= 0),
  last_seen TEXT NOT NULL,
  present INTEGER NOT NULL DEFAULT 1 CHECK (present IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- migrate:split
CREATE INDEX library_tracks_present_path_idx
ON library_tracks(present, relative_path);
-- migrate:split
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  status TEXT NOT NULL,
  configuration TEXT NOT NULL,
  parent_job_id TEXT REFERENCES jobs(id),
  total_items INTEGER NOT NULL CHECK (total_items >= 0),
  completed_items INTEGER NOT NULL DEFAULT 0 CHECK (completed_items >= 0),
  failed_items INTEGER NOT NULL DEFAULT 0 CHECK (failed_items >= 0),
  cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TEXT,
  finished_at TEXT
);
-- migrate:split
CREATE TABLE job_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  value TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  result TEXT,
  error TEXT,
  UNIQUE(job_id, position)
);
-- migrate:split
CREATE INDEX job_items_job_position_idx ON job_items(job_id, position);
-- migrate:split
CREATE TABLE events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- migrate:split
CREATE INDEX events_job_sequence_idx ON events(job_id, sequence);
