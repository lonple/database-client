-- 测评用例关联影子会话，便于画布复看工作日志并再次执行
ALTER TABLE askdata.eval_task_case
    ADD COLUMN IF NOT EXISTS session_id BIGINT;
CREATE INDEX IF NOT EXISTS idx_eval_task_case_session ON askdata.eval_task_case(session_id);
