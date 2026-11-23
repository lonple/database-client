-- 问数侧知识索引：仅存问数特有属性 + ada-memory 文章 id
-- 查询：先按类型/元数据作用域过滤 → 拿 document_id 再查 memory

CREATE TABLE IF NOT EXISTS askdata.ask_knowledge (
    id                 BIGSERIAL PRIMARY KEY,
    document_id        BIGINT       NOT NULL,
    knowledge_category VARCHAR(32)  NOT NULL,
    slice_logic        VARCHAR(32)  NOT NULL DEFAULT 'AI_SUGGEST',
    slice_rule         TEXT,
    workspace_id       BIGINT,
    connection_id      BIGINT,
    database_name      VARCHAR(256),
    schema_name        VARCHAR(256),
    connection_name    VARCHAR(256),
    db_type            VARCHAR(64),
    owner_user_id      BIGINT       NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted            BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT uk_ask_knowledge_document UNIQUE (document_id),
    CONSTRAINT ck_ask_knowledge_category CHECK (knowledge_category IN ('GENERAL', 'METADATA'))
);

-- 表可能已由早期 V5 创建（无切片列）：先补列再注释
ALTER TABLE askdata.ask_knowledge ADD COLUMN IF NOT EXISTS slice_logic VARCHAR(32) NOT NULL DEFAULT 'AI_SUGGEST';
ALTER TABLE askdata.ask_knowledge ADD COLUMN IF NOT EXISTS slice_rule TEXT;
ALTER TABLE askdata.ask_knowledge DROP COLUMN IF EXISTS product_name;
ALTER TABLE askdata.ask_knowledge DROP COLUMN IF EXISTS title;
ALTER TABLE askdata.ask_knowledge DROP COLUMN IF EXISTS summary;

CREATE INDEX IF NOT EXISTS idx_ask_knowledge_owner ON askdata.ask_knowledge(owner_user_id) WHERE deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_ask_knowledge_category ON askdata.ask_knowledge(knowledge_category) WHERE deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_ask_knowledge_scope
    ON askdata.ask_knowledge(connection_id, database_name, schema_name)
    WHERE deleted = FALSE AND knowledge_category = 'METADATA';

COMMENT ON TABLE askdata.ask_knowledge IS '问数知识索引：类型+切片规则+元数据过滤+memory文章id；正文/切片/向量在ada-memory';
COMMENT ON COLUMN askdata.ask_knowledge.document_id IS 'ada-memory 文档 id';
COMMENT ON COLUMN askdata.ask_knowledge.knowledge_category IS 'GENERAL | METADATA';
COMMENT ON COLUMN askdata.ask_knowledge.slice_logic IS '切片方式，当前默认 AI_SUGGEST';
COMMENT ON COLUMN askdata.ask_knowledge.slice_rule IS '切片规则话术';
COMMENT ON COLUMN askdata.ask_knowledge.connection_id IS '元数据：过滤连接';
COMMENT ON COLUMN askdata.ask_knowledge.database_name IS '元数据：过滤库';
COMMENT ON COLUMN askdata.ask_knowledge.schema_name IS '元数据：过滤模式';
