ALTER TABLE library_tracks ADD COLUMN artist TEXT;
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN title TEXT;
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN album TEXT;
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN duration_seconds REAL;
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN metadata_source TEXT;
