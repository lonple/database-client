-- 用户日 token 配额、幂等、图中断快照

CREATE TABLE IF NOT EXISTS askdata.ask_user_token_daily (
    user_id      BIGINT NOT NULL,
    usage_date   DATE NOT NULL,
    tokens_used  BIGINT NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, usage_date)
);

CREATE TABLE IF NOT EXISTS askdata.ask_idempotency (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    route           VARCHAR(64) NOT NULL,
    request_hash    VARCHAR(64),
    status          VARCHAR(16) NOT NULL DEFAULT 'RUNNING',
    response_json   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    UNIQUE (user_id, idempotency_key, route)
);

CREATE INDEX IF NOT EXISTS idx_ask_idempotency_created
    ON askdata.ask_idempotency (created_at);

CREATE TABLE IF NOT EXISTS askdata.ask_graph_checkpoint (
    id                BIGSERIAL PRIMARY KEY,
    session_id        BIGINT NOT NULL,
    hitl_id           BIGINT,
    status            VARCHAR(16) NOT NULL DEFAULT 'INTERRUPTED',
    interrupted_node  VARCHAR(64),
    resume_from       VARCHAR(64),
    state_json        JSONB NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ask_graph_checkpoint_session
    ON askdata.ask_graph_checkpoint (session_id, status);

CREATE INDEX IF NOT EXISTS idx_ask_graph_checkpoint_hitl
    ON askdata.ask_graph_checkpoint (hitl_id);
