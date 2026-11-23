-- 会话记忆：事实卡 + 对话摘要（问数上下文压缩）
ALTER TABLE askdata.ask_session
    ADD COLUMN IF NOT EXISTS fact_card JSONB,
    ADD COLUMN IF NOT EXISTS conversation_summary TEXT,
    ADD COLUMN IF NOT EXISTS summary_message_count INT NOT NULL DEFAULT 0;
