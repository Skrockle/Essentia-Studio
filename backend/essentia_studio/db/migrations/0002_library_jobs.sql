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
