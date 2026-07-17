CREATE TABLE app_settings (
  singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
  worker_count INTEGER NOT NULL CHECK (worker_count BETWEEN 1 AND 64),
  max_audio_seconds INTEGER NOT NULL CHECK (max_audio_seconds BETWEEN 1 AND 3600),
  genre_threshold REAL NOT NULL CHECK (genre_threshold BETWEEN 0 AND 1),
  mood_threshold REAL NOT NULL CHECK (mood_threshold BETWEEN 0 AND 1),
  genre_count INTEGER NOT NULL CHECK (genre_count BETWEEN 1 AND 20),
  write_confidence_tags INTEGER NOT NULL CHECK (write_confidence_tags IN (0, 1)),
  overwrite_existing INTEGER NOT NULL CHECK (overwrite_existing IN (0, 1)),
  compute_preference TEXT NOT NULL CHECK (compute_preference IN ('auto', 'cpu', 'cuda'))
);
-- migrate:split
INSERT INTO app_settings VALUES (1, 1, 300, 0.25, 0.10, 3, 1, 0, 'auto');
