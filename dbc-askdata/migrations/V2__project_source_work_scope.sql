ALTER TABLE askdata.ask_project
    ADD COLUMN IF NOT EXISTS source_connection_id BIGINT,
    ADD COLUMN IF NOT EXISTS source_database VARCHAR(256),
    ADD COLUMN IF NOT EXISTS source_schema VARCHAR(256),
    ADD COLUMN IF NOT EXISTS work_database VARCHAR(256),
    ADD COLUMN IF NOT EXISTS work_schema VARCHAR(256);

UPDATE askdata.ask_project
SET source_connection_id = work_connection_id
WHERE source_connection_id IS NULL;

ALTER TABLE askdata.ask_project
    ALTER COLUMN source_connection_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ask_project_source_conn
    ON askdata.ask_project (source_connection_id)
    WHERE deleted = FALSE;
