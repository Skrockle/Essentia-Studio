ALTER TABLE library_tracks ADD COLUMN managed_genres TEXT NOT NULL DEFAULT '[]';
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_moods TEXT NOT NULL DEFAULT '[]';
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_tags_status TEXT NOT NULL DEFAULT 'unknown'
  CHECK (managed_tags_status IN ('unknown', 'ok', 'error'));
-- migrate:split
ALTER TABLE library_tracks ADD COLUMN managed_tags_error_code TEXT;
-- migrate:split
CREATE INDEX library_tracks_managed_tag_status_idx
ON library_tracks(present, managed_tags_status);
