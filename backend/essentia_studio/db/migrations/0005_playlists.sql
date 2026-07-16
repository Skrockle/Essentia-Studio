CREATE TABLE playlist_records (
  filename TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  source_mode TEXT NOT NULL,
  definition TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- migrate:split
CREATE TABLE playlist_operations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  operation TEXT NOT NULL,
  success INTEGER NOT NULL CHECK (success IN (0, 1)),
  fingerprint TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
