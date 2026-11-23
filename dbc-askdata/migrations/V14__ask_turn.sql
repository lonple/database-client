-- 一次问数头表 + span.turn_id（列表查头表，详情按下钻 span）

CREATE TABLE IF NOT EXISTS askdata.ask_turn (
    id              BIGSERIAL PRIMARY KEY,
    root_trace_id   VARCHAR(64) NOT NULL,
    question        TEXT NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
    workspace_id    BIGINT,
    project_id      BIGINT,
    session_id      BIGINT,
    user_id         BIGINT,
    hitl_id         BIGINT,
    route           VARCHAR(16),
    token_in        INT NOT NULL DEFAULT 0,
    token_out       INT NOT NULL DEFAULT 0,
    span_count      INT NOT NULL DEFAULT 0,
    latency_ms      INT,
    error_message   VARCHAR(1024),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    CONSTRAINT uq_ask_turn_root_trace UNIQUE (root_trace_id)
);

CREATE INDEX IF NOT EXISTS idx_ask_turn_started ON askdata.ask_turn (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ask_turn_ws ON askdata.ask_turn (workspace_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ask_turn_session ON askdata.ask_turn (session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_ask_turn_status ON askdata.ask_turn (status);

ALTER TABLE askdata.ask_llm_span
    ADD COLUMN IF NOT EXISTS turn_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_ask_span_turn ON askdata.ask_llm_span (turn_id, id);
