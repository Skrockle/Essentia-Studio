ALTER TABLE write_operations
ADD COLUMN trigger TEXT NOT NULL DEFAULT 'manual'
CHECK (trigger IN ('manual', 'automation'));
