ALTER TABLE write_operations
ADD COLUMN requested_tags TEXT;
-- migrate:split
UPDATE write_operations
SET requested_tags = (
  SELECT json_object(
    'genres', json(tag_drafts.genres),
    'moods', json(tag_drafts.moods)
  )
  FROM tag_drafts
  WHERE tag_drafts.result_id = write_operations.result_id
)
WHERE status IN ('verified', 'undone');
