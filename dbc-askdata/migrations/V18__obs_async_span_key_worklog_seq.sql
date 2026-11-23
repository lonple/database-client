-- 观测异步化：span_key UUID；工作日志 seq 作轮询游标

ALTER TABLE askdata.ask_work_log
    ADD COLUMN IF NOT EXISTS seq BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ask_work_log_turn_seq
    ON askdata.ask_work_log (turn_id, seq)
    WHERE seq IS NOT NULL;

ALTER TABLE askdata.ask_llm_span
    ADD COLUMN IF NOT EXISTS span_key VARCHAR(36);

ALTER TABLE askdata.ask_llm_span
    ADD COLUMN IF NOT EXISTS parent_span_key VARCHAR(36);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ask_llm_span_key
    ON askdata.ask_llm_span (span_key)
    WHERE span_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ask_llm_span_parent_key
    ON askdata.ask_llm_span (parent_span_key)
    WHERE parent_span_key IS NOT NULL;
