-- 智能问数测评域（可重复执行）
-- ask_project.hidden：测评影子工程不出现在人工问数树

ALTER TABLE askdata.ask_project
    ADD COLUMN IF NOT EXISTS hidden BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS askdata.eval_template (
    id           BIGSERIAL PRIMARY KEY,
    code         VARCHAR(64)  NOT NULL UNIQUE,
    name         VARCHAR(128) NOT NULL,
    version      VARCHAR(32)  NOT NULL DEFAULT 'v1',
    remark       VARCHAR(512),
    enabled      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS askdata.eval_project (
    id                    BIGSERIAL PRIMARY KEY,
    workspace_id          BIGINT       NOT NULL,
    name                  VARCHAR(128) NOT NULL,
    remark                VARCHAR(512),
    template_id           BIGINT       NOT NULL REFERENCES askdata.eval_template(id),
    source_connection_id  BIGINT       NOT NULL,
    source_database       VARCHAR(128),
    source_schema         VARCHAR(128),
    work_connection_id    BIGINT       NOT NULL,
    work_database         VARCHAR(128),
    work_schema           VARCHAR(128),
    ask_project_id        BIGINT       NOT NULL,
    owner_user_id         BIGINT       NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_eval_project_ws ON askdata.eval_project(workspace_id);
CREATE INDEX IF NOT EXISTS idx_eval_project_owner ON askdata.eval_project(owner_user_id);

CREATE TABLE IF NOT EXISTS askdata.eval_case (
    id                 BIGSERIAL PRIMARY KEY,
    case_key           VARCHAR(64)  NOT NULL UNIQUE,
    scope              VARCHAR(32)  NOT NULL,
    template_id        BIGINT       REFERENCES askdata.eval_template(id),
    project_id         BIGINT       REFERENCES askdata.eval_project(id) ON DELETE CASCADE,
    category           VARCHAR(64)  NOT NULL,
    govern_subtype     VARCHAR(32),
    question           TEXT         NOT NULL,
    expect_sql         TEXT,
    compare_mode       VARCHAR(32)  NOT NULL,
    compare_spec_json  JSONB        NOT NULL DEFAULT '{}',
    hitl_replies_json  JSONB,
    tags_json          JSONB,
    difficulty         SMALLINT,
    enabled            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_eval_case_scope CHECK (
        (scope = 'TEMPLATE' AND template_id IS NOT NULL AND project_id IS NULL)
        OR (scope = 'PROJECT_CUSTOM' AND project_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_eval_case_tpl ON askdata.eval_case(template_id);
CREATE INDEX IF NOT EXISTS idx_eval_case_proj ON askdata.eval_case(project_id);
CREATE INDEX IF NOT EXISTS idx_eval_case_category ON askdata.eval_case(category);

CREATE TABLE IF NOT EXISTS askdata.eval_task (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT       NOT NULL REFERENCES askdata.eval_project(id),
    workspace_id    BIGINT       NOT NULL,
    name            VARCHAR(128) NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    metrics_json    JSONB,
    error_message   TEXT,
    created_by      BIGINT       NOT NULL,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_eval_task_ws ON askdata.eval_task(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_eval_task_proj ON askdata.eval_task(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS askdata.eval_task_case (
    id                   BIGSERIAL PRIMARY KEY,
    task_id              BIGINT       NOT NULL REFERENCES askdata.eval_task(id) ON DELETE CASCADE,
    case_id              BIGINT,
    case_key             VARCHAR(64)  NOT NULL,
    question             TEXT         NOT NULL,
    expect_sql           TEXT,
    compare_mode         VARCHAR(32)  NOT NULL,
    compare_spec_json    JSONB        NOT NULL DEFAULT '{}',
    govern_subtype       VARCHAR(32),
    hitl_replies_json    JSONB,
    status               VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    ask_sql              TEXT,
    ask_error            TEXT,
    hitl_rounds          INT          NOT NULL DEFAULT 0,
    compare_score        NUMERIC(8,4),
    compare_detail_json  JSONB,
    expect_row_count     INT,
    ask_row_count        INT,
    trace_id             VARCHAR(64),
    workflow_id          BIGINT,
    run_id               BIGINT,
    started_at           TIMESTAMPTZ,
    finished_at          TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_eval_task_case_task ON askdata.eval_task_case(task_id, status);
