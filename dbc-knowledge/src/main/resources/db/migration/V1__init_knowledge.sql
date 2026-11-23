-- 知识库唯一 init（无增量迁移）。
-- 共用平台库 postgres；仅使用 knowledge schema。
-- 向量与全文在 Milvus（ada_document / ada_slice）；本 schema 只存业务元数据与向量同步事件。
-- 结构变更：改本文件后 DROP SCHEMA knowledge CASCADE，再重启 dbc-knowledge 由 Flyway 重建。

CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE knowledge.t_knowledge_category (
    id          BIGSERIAL PRIMARY KEY,
    parent_id   BIGINT REFERENCES knowledge.t_knowledge_category(id),
    name        VARCHAR(128) NOT NULL,
    code        VARCHAR(64)  NOT NULL,
    path        VARCHAR(512) NOT NULL DEFAULT '',
    sort_no     INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_category_parent_name UNIQUE (parent_id, name),
    CONSTRAINT uk_category_code UNIQUE (code)
);

CREATE INDEX idx_category_path ON knowledge.t_knowledge_category(path);

CREATE TABLE knowledge.t_knowledge_document (
    id                    BIGSERIAL PRIMARY KEY,
    title                 VARCHAR(256) NOT NULL,
    product_name          VARCHAR(128),
    orientation           VARCHAR(32)  NOT NULL,
    source_type           VARCHAR(32)  NOT NULL DEFAULT 'MANUAL',
    body                  TEXT         NOT NULL DEFAULT '',
    status                VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',
    category_id           BIGINT REFERENCES knowledge.t_knowledge_category(id),
    summary               VARCHAR(512) NOT NULL DEFAULT '',
    created_by            VARCHAR(64),
    vector_sync_status    VARCHAR(16)  NOT NULL DEFAULT 'NONE',
    lineage_id            BIGINT,
    version_no            INT          NOT NULL DEFAULT 1,
    update_mode           VARCHAR(32)  NOT NULL DEFAULT 'CREATE',
    replaces_document_id  BIGINT,
    expire_slice_ids      TEXT         NOT NULL DEFAULT '[]',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at          TIMESTAMPTZ
);

COMMENT ON COLUMN knowledge.t_knowledge_document.orientation IS 'HORIZONTAL | VERTICAL | BOTH';
COMMENT ON COLUMN knowledge.t_knowledge_document.summary IS '原文简介（必填）；参与原文摘要向量';
COMMENT ON COLUMN knowledge.t_knowledge_document.vector_sync_status IS 'NONE | PENDING | SYNCED | UNSYNCED';
COMMENT ON COLUMN knowledge.t_knowledge_document.lineage_id IS '版本脉络；同 lineage 共享版本号序列';
COMMENT ON COLUMN knowledge.t_knowledge_document.version_no IS '同一次发布共享的版本号（原文与其切片）';
COMMENT ON COLUMN knowledge.t_knowledge_document.update_mode IS 'CREATE | REPLACE_DOCUMENT | REPLACE_SLICES';
COMMENT ON COLUMN knowledge.t_knowledge_document.replaces_document_id IS '更新目标已发布原文';
COMMENT ON COLUMN knowledge.t_knowledge_document.expire_slice_ids IS 'JSON 数组；REPLACE_SLICES 时待过期切片 id';

CREATE INDEX idx_document_status ON knowledge.t_knowledge_document(status);
CREATE INDEX idx_document_vector_sync ON knowledge.t_knowledge_document(vector_sync_status);
CREATE INDEX idx_document_lineage ON knowledge.t_knowledge_document(lineage_id, version_no);

CREATE TABLE knowledge.t_knowledge_slice (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES knowledge.t_knowledge_document(id) ON DELETE CASCADE,
    seq_no        INT NOT NULL DEFAULT 0,
    title         VARCHAR(256) NOT NULL,
    description   VARCHAR(2048) NOT NULL DEFAULT '',
    body_summary  VARCHAR(2048) NOT NULL DEFAULT '',
    body          TEXT NOT NULL DEFAULT '',
    tech_tags     TEXT[] NOT NULL DEFAULT '{}',
    orientation   VARCHAR(16) NOT NULL DEFAULT 'HORIZONTAL',
    category_id   BIGINT REFERENCES knowledge.t_knowledge_category(id),
    status        VARCHAR(16) NOT NULL DEFAULT 'DRAFT',
    version_no    INT NOT NULL DEFAULT 1,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at  TIMESTAMPTZ
);

COMMENT ON COLUMN knowledge.t_knowledge_slice.title IS '切片标题；稠密向量';
COMMENT ON COLUMN knowledge.t_knowledge_slice.description IS '切片说明；稠密向量';
COMMENT ON COLUMN knowledge.t_knowledge_slice.body_summary IS '正文摘要；稠密向量';
COMMENT ON COLUMN knowledge.t_knowledge_slice.body IS '切片正文；仅 BM25';
COMMENT ON COLUMN knowledge.t_knowledge_slice.version_no IS '与所属原文同一次发布共享的版本号';

CREATE INDEX idx_slice_document ON knowledge.t_knowledge_slice(document_id, seq_no);
CREATE INDEX idx_slice_category ON knowledge.t_knowledge_slice(category_id, status);

CREATE TABLE knowledge.t_knowledge_relation (
    id         BIGSERIAL PRIMARY KEY,
    from_kind  VARCHAR(16) NOT NULL,
    from_id    BIGINT NOT NULL,
    to_kind    VARCHAR(16) NOT NULL,
    to_id      BIGINT NOT NULL,
    rel_type   VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_relation UNIQUE (from_kind, from_id, to_kind, to_id, rel_type)
);

CREATE TABLE knowledge.t_knowledge_unit_index (
    id              BIGSERIAL PRIMARY KEY,
    kind            VARCHAR(16) NOT NULL,
    ref_id          BIGINT NOT NULL,
    document_id     BIGINT,
    title           VARCHAR(256) NOT NULL,
    description     VARCHAR(2048) NOT NULL DEFAULT '',
    body_summary    VARCHAR(2048) NOT NULL DEFAULT '',
    body            TEXT NOT NULL DEFAULT '',
    category_id     BIGINT,
    status          VARCHAR(16) NOT NULL,
    tech_tags       TEXT[] NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_unit_kind_ref UNIQUE (kind, ref_id)
);

COMMENT ON COLUMN knowledge.t_knowledge_unit_index.description IS 'DOCUMENT=原文简介；SLICE=切片说明';
COMMENT ON COLUMN knowledge.t_knowledge_unit_index.body_summary IS 'SLICE=正文摘要；DOCUMENT 为空';

CREATE INDEX idx_unit_category ON knowledge.t_knowledge_unit_index(category_id, status);
CREATE INDEX idx_unit_document ON knowledge.t_knowledge_unit_index(document_id);

CREATE TABLE knowledge.t_knowledge_vector_sync_event (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL,
    op_type       VARCHAR(16) NOT NULL,
    status        VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    retry_count   INT NOT NULL DEFAULT 0,
    max_retries   INT NOT NULL DEFAULT 2,
    next_retry_at TIMESTAMPTZ,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN knowledge.t_knowledge_vector_sync_event.op_type IS 'UPSERT | DELETE';
COMMENT ON COLUMN knowledge.t_knowledge_vector_sync_event.status IS 'PENDING | SUCCESS | FAILED';

CREATE INDEX idx_vector_sync_pending ON knowledge.t_knowledge_vector_sync_event(status, next_retry_at);
CREATE INDEX idx_vector_sync_document ON knowledge.t_knowledge_vector_sync_event(document_id);

INSERT INTO knowledge.t_knowledge_category (name, code, path, sort_no) VALUES
    ('元数据', 'METADATA', '/METADATA', 10),
    ('通用知识', 'GENERAL', '/GENERAL', 20),
    ('问句知识', 'QUESTION', '/QUESTION', 30);