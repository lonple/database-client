-- 问数实时进度日志按 turn 持久化，供工作台按轮次回看

CREATE TABLE IF NOT EXISTS askdata.ask_work_log (
    id           BIGSERIAL PRIMARY KEY,
    turn_id      BIGINT NOT NULL,
    session_id   BIGINT NOT NULL,
    level        VARCHAR(16) NOT NULL DEFAULT 'INFO',
    message      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ask_work_log_turn ON askdata.ask_work_log (turn_id, id);
CREATE INDEX IF NOT EXISTS idx_ask_work_log_session ON askdata.ask_work_log (session_id, id);
