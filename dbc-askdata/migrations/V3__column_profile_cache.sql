-- 列画像缓存
CREATE TABLE IF NOT EXISTS askdata.ask_column_profile_cache (
    id                  BIGSERIAL PRIMARY KEY,
    workspace_id        BIGINT NOT NULL,
    connection_id       BIGINT NOT NULL,
    database_name       VARCHAR(256),
    schema_name         VARCHAR(256),
    table_name          VARCHAR(256) NOT NULL,
    column_name         VARCHAR(256) NOT NULL,
    profile_json        JSONB NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_ask_profile_scope
    ON askdata.ask_column_profile_cache (
        workspace_id, connection_id, table_name, column_name, database_name, schema_name
    );
CREATE INDEX IF NOT EXISTS idx_ask_profile_expires
    ON askdata.ask_column_profile_cache (expires_at);
