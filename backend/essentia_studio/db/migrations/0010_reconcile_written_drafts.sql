UPDATE tag_drafts AS draft
SET selected = 0,
    updated_at = CURRENT_TIMESTAMP
WHERE draft.selected = 1
  AND EXISTS (
    SELECT 1
    FROM write_operations AS operation
    JOIN analysis_results AS analysis ON analysis.id = operation.result_id
    JOIN library_tracks AS track ON track.id = analysis.track_id
    WHERE operation.result_id = draft.result_id
      AND operation.id = (
        SELECT latest.id
        FROM write_operations AS latest
        WHERE latest.result_id = draft.result_id
        ORDER BY latest.created_at DESC, latest.id DESC
        LIMIT 1
      )
      AND operation.status = 'verified'
      AND operation.post_write_size = track.size
      AND operation.post_write_mtime_ns = track.mtime_ns
      AND json_extract(operation.requested_tags, '$.genres') = json(draft.genres)
      AND json_extract(operation.requested_tags, '$.moods') = json(draft.moods)
  );
