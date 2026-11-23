-- HITL 确认卡片 + 知识绑定分类扩展 INTENT_TABLE

CREATE TABLE IF NOT EXISTS askdata.ask_hitl_card (
    id                 BIGSERIAL PRIMARY KEY,
    hitl_id            BIGINT       NOT NULL,
    session_id         BIGINT       NOT NULL,
    project_id         BIGINT,
    connection_id      BIGINT       NOT NULL,
    database_name      VARCHAR(256),
    schema_name        VARCHAR(256),
    kind               VARCHAR(32)  NOT NULL,
    surface            TEXT         NOT NULL DEFAULT '',
    target_table       VARCHAR(256),
    target_column      VARCHAR(256),
    target_value       TEXT,
    question           TEXT,
    payload            JSONB,
    status             VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    promote_meta       JSONB,
    owner_user_id      BIGINT       NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    promoted_at        TIMESTAMPTZ,
    CONSTRAINT ck_ask_hitl_card_status
        CHECK (status IN ('PENDING', 'PROMOTED', 'CONFLICT', 'SKIPPED', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_ask_hitl_card_session_status
    ON askdata.ask_hitl_card (session_id, status, id);

CREATE UNIQUE INDEX IF NOT EXISTS uk_ask_hitl_card_hitl
    ON askdata.ask_hitl_card (hitl_id);

CREATE INDEX IF NOT EXISTS idx_ask_hitl_card_scope_kind
    ON askdata.ask_hitl_card (connection_id, database_name, schema_name, kind)
    WHERE status = 'PENDING';

COMMENT ON TABLE askdata.ask_hitl_card IS
    'HITL 确认卡片：resolve 落草稿，有用/记忆时归并进 INTENT_TABLE 或 METADATA 表文字典';
COMMENT ON COLUMN askdata.ask_hitl_card.surface IS '业务说法/意图原文（合并键之一）';
COMMENT ON COLUMN askdata.ask_hitl_card.target_value IS '确认的码值或补充文本';

-- 绑定分类：增加 INTENT_TABLE（意图→表专用知识）
ALTER TABLE askdata.ask_knowledge_binding
    DROP CONSTRAINT IF EXISTS ck_ask_kb_binding_category;

ALTER TABLE askdata.ask_knowledge_binding
    ADD CONSTRAINT ck_ask_kb_binding_category
    CHECK (knowledge_category IN ('GENERAL', 'METADATA', 'QUESTION', 'INTENT_TABLE'));

COMMENT ON COLUMN askdata.ask_knowledge_binding.knowledge_category IS
    'GENERAL | METADATA | QUESTION | INTENT_TABLE';
