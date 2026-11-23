-- 应用运行配置（系统管理 · 应用配置）

CREATE TABLE IF NOT EXISTS askdata.ask_app_config (
    module       VARCHAR(64) PRIMARY KEY,
    config_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by   BIGINT,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE askdata.ask_app_config IS '应用业务运行配置；module=askdata 含 llmProvider/dailyTokenLimit/concurrentChatLimit/evalTaskConcurrency';
