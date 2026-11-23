-- 画布执行成功后的有用/无用/保存记忆（按 run+user 幂等）

CREATE TABLE IF NOT EXISTS askdata.ask_run_feedback (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT NOT NULL,
    workflow_id     BIGINT NOT NULL,
    session_id      BIGINT,
    user_id         BIGINT NOT NULL,
    useful_done     BOOLEAN NOT NULL DEFAULT FALSE,
    useless_done    BOOLEAN NOT NULL DEFAULT FALSE,
    memory_done     BOOLEAN NOT NULL DEFAULT FALSE,
    sample_id       BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ask_run_feedback_run_user UNIQUE (run_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_ask_run_feedback_wf
    ON askdata.ask_run_feedback (workflow_id, user_id);
