-- 平台库 schema askdata 初始化（可重复执行）
CREATE SCHEMA IF NOT EXISTS askdata;

CREATE TABLE IF NOT EXISTS askdata.ask_project (
    id                  BIGSERIAL PRIMARY KEY,
    name                VARCHAR(128) NOT NULL,
    description         VARCHAR(512),
    workspace_id        BIGINT NOT NULL,
    source_connection_id BIGINT NOT NULL,
    source_database     VARCHAR(256),
    source_schema       VARCHAR(256),
    work_connection_id  BIGINT NOT NULL,
    work_database       VARCHAR(256),
    work_schema         VARCHAR(256),
    owner_user_id       BIGINT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted             BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_ask_project_ws ON askdata.ask_project (workspace_id) WHERE deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_ask_project_owner ON askdata.ask_project (owner_user_id) WHERE deleted = FALSE;

CREATE TABLE IF NOT EXISTS askdata.ask_session (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL,
    title           VARCHAR(256),
    owner_user_id   BIGINT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ask_session_project ON askdata.ask_session (project_id);

CREATE TABLE IF NOT EXISTS askdata.ask_message (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL,
    role            VARCHAR(32) NOT NULL,
    content         TEXT NOT NULL,
    content_type    VARCHAR(32) NOT NULL DEFAULT 'text',
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ask_message_session ON askdata.ask_message (session_id);

CREATE TABLE IF NOT EXISTS askdata.ask_hitl (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    question        TEXT NOT NULL,
    options         JSONB,
    resolution      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ask_hitl_session ON askdata.ask_hitl (session_id);

CREATE TABLE IF NOT EXISTS askdata.ask_workflow_draft (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL,
    session_id      BIGINT,
    name            VARCHAR(128),
    nodes_json      JSONB NOT NULL,
    owner_user_id   BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ask_draft_project ON askdata.ask_workflow_draft (project_id);

CREATE TABLE IF NOT EXISTS askdata.ask_workflow (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT NOT NULL,
    name            VARCHAR(128) NOT NULL,
    description     VARCHAR(512),
    nodes_json      JSONB NOT NULL,
    owner_user_id   BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted         BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_ask_workflow_project ON askdata.ask_workflow (project_id) WHERE deleted = FALSE;

CREATE TABLE IF NOT EXISTS askdata.ask_workflow_run (
    id                  BIGSERIAL PRIMARY KEY,
    workflow_id         BIGINT NOT NULL,
    project_id          BIGINT NOT NULL,
    session_id          BIGINT,
    status              VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    result_table_fqn    VARCHAR(256),
    cancel_token        VARCHAR(64),
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    owner_user_id       BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ask_run_workflow ON askdata.ask_workflow_run (workflow_id);
CREATE INDEX IF NOT EXISTS idx_ask_run_project ON askdata.ask_workflow_run (project_id);

CREATE TABLE IF NOT EXISTS askdata.ask_workflow_run_node (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT NOT NULL,
    node_id         VARCHAR(64) NOT NULL,
    node_type       VARCHAR(32) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    sql_text        TEXT,
    temp_table_fqn  VARCHAR(256),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ask_run_node_run ON askdata.ask_workflow_run_node (run_id);

CREATE TABLE IF NOT EXISTS askdata.ask_workflow_run_log (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT NOT NULL,
    level           VARCHAR(16) NOT NULL DEFAULT 'INFO',
    message         TEXT NOT NULL,
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ask_run_log_run ON askdata.ask_workflow_run_log (run_id);

CREATE TABLE IF NOT EXISTS askdata.ask_workflow_run_result (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT NOT NULL UNIQUE,
    columns_json    JSONB,
    rows_json       JSONB,
    row_count       INT NOT NULL DEFAULT 0,
    truncated       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS askdata.ask_llm_span (
    id              BIGSERIAL PRIMARY KEY,
    trace_id        VARCHAR(64),
    parent_span_id  BIGINT,
    workspace_id    BIGINT,
    project_id      BIGINT,
    session_id      BIGINT,
    run_id          BIGINT,
    user_id         BIGINT,
    phase           VARCHAR(16) NOT NULL,
    kind            VARCHAR(16) NOT NULL,
    name            VARCHAR(128) NOT NULL,
    residency       VARCHAR(16),
    model           VARCHAR(64),
    status          VARCHAR(16) NOT NULL DEFAULT 'OK',
    latency_ms      INT,
    token_in        INT,
    token_out       INT,
    error_code      VARCHAR(64),
    error_message   VARCHAR(1024),
    payload_meta    JSONB,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ask_span_trace ON askdata.ask_llm_span (trace_id);
CREATE INDEX IF NOT EXISTS idx_ask_span_ws ON askdata.ask_llm_span (workspace_id);
CREATE INDEX IF NOT EXISTS idx_ask_span_started ON askdata.ask_llm_span (started_at DESC);
