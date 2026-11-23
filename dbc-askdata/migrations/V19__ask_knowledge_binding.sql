-- 问数知识绑定：连接/库/模式 → ada-memory 文档 id（可删重建，不兼容旧 ask_knowledge）
-- 启动迁移按文件全量重跑，须幂等

DROP TABLE IF EXISTS askdata.ask_knowledge CASCADE;

CREATE TABLE IF NOT EXISTS askdata.ask_knowledge_binding (
    id                 BIGSERIAL PRIMARY KEY,
    name               VARCHAR(128) NOT NULL,
    workspace_id       BIGINT,
    connection_id      BIGINT       NOT NULL,
    connection_name    VARCHAR(256),
    database_name      VARCHAR(256),
    schema_name        VARCHAR(256),
    document_id        BIGINT       NOT NULL,
    document_name      VARCHAR(256),
    knowledge_category VARCHAR(32)  NOT NULL,
    involved_tables    JSONB,
    remark             VARCHAR(512),
    owner_user_id      BIGINT       NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted            BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_ask_kb_binding_category
        CHECK (knowledge_category IN ('GENERAL', 'METADATA', 'QUESTION'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_ask_kb_binding_scope_doc
    ON askdata.ask_knowledge_binding (
        connection_id,
        COALESCE(database_name, ''),
        COALESCE(schema_name, ''),
        document_id
    )
    WHERE deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_ask_kb_binding_owner
    ON askdata.ask_knowledge_binding(owner_user_id)
    WHERE deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_ask_kb_binding_category_scope
    ON askdata.ask_knowledge_binding(
        knowledge_category, connection_id, database_name, schema_name
    )
    WHERE deleted = FALSE;

COMMENT ON TABLE askdata.ask_knowledge_binding IS
    '问数知识绑定：按连接/库/模式绑定 ada-memory 文档；生成 SQL 时按作用域取 document_id';
COMMENT ON COLUMN askdata.ask_knowledge_binding.document_id IS 'ada-memory 文档 id';
COMMENT ON COLUMN askdata.ask_knowledge_binding.knowledge_category IS 'GENERAL | METADATA | QUESTION';
COMMENT ON COLUMN askdata.ask_knowledge_binding.involved_tables IS '问句知识涉表（可选）';
