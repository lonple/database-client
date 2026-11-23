-- 库表关系绑定：连接/库/模式 → ada-graph 图谱 id

CREATE TABLE IF NOT EXISTS askdata.ask_table_relation_binding (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    workspace_id    BIGINT,
    connection_id   BIGINT       NOT NULL,
    connection_name VARCHAR(256),
    database_name   VARCHAR(256),
    schema_name     VARCHAR(256),
    graph_id        BIGINT       NOT NULL,
    graph_name      VARCHAR(256),
    remark          VARCHAR(512),
    owner_user_id   BIGINT       NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted         BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_ask_table_rel_scope
    ON askdata.ask_table_relation_binding (
        connection_id,
        COALESCE(database_name, ''),
        COALESCE(schema_name, '')
    )
    WHERE deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_ask_table_rel_owner
    ON askdata.ask_table_relation_binding(owner_user_id)
    WHERE deleted = FALSE;

COMMENT ON TABLE askdata.ask_table_relation_binding IS
    '问数库表关系：按连接/库/模式绑定 ada-graph 图谱，生成 SQL 时查最短 JOIN 路径';
