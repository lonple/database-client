-- 文档管理：源文件元数据 + Markdown；原件在 DOCUMENTS_DIR

CREATE TABLE IF NOT EXISTS askdata.ask_document (
    id                     BIGSERIAL PRIMARY KEY,
    owner_user_id          BIGINT       NOT NULL,
    name                   VARCHAR(256) NOT NULL,
    source_format          VARCHAR(16)  NOT NULL,
    source_filename        VARCHAR(512) NOT NULL,
    source_relpath         VARCHAR(1024) NOT NULL,
    pipeline               VARCHAR(16)  NOT NULL,
    convert_status         VARCHAR(16)  NOT NULL DEFAULT 'QUEUED',
    convert_error          TEXT,
    markdown               TEXT,
    markdown_from_convert  TEXT,
    markdown_edited        BOOLEAN      NOT NULL DEFAULT FALSE,
    knowledge_document_id  BIGINT,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    deleted                BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_ask_document_pipeline CHECK (pipeline IN ('DOCUMENT', 'IMAGE')),
    CONSTRAINT ck_ask_document_status CHECK (convert_status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS idx_ask_document_owner
    ON askdata.ask_document(owner_user_id) WHERE deleted = FALSE;

COMMENT ON TABLE askdata.ask_document IS '问数文档管理：转换状态与 Markdown；原件在配置目录';
