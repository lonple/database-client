-- 已确认问数样本（执行成功且用户点正确）：只存 workflowId，SQL 用时现查
CREATE TABLE IF NOT EXISTS askdata.ask_verified_sample (
    id              BIGSERIAL PRIMARY KEY,
    session_id      BIGINT NOT NULL,
    project_id      BIGINT NOT NULL,
    workflow_id     BIGINT NOT NULL,
    question        TEXT NOT NULL,
    hitl_resolution JSONB,
    run_id          BIGINT,
    owner_user_id   BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ask_verified_sample_session
    ON askdata.ask_verified_sample (session_id, id DESC);

CREATE INDEX IF NOT EXISTS idx_ask_verified_sample_project
    ON askdata.ask_verified_sample (project_id, id DESC);

-- 问句知识：AskKnowledge.knowledge_category=QUESTION；涉表名列表供多路召回展开
-- 分类约束放宽见 V11__ask_knowledge_category_question.sql
ALTER TABLE askdata.ask_knowledge
    ADD COLUMN IF NOT EXISTS involved_tables JSONB;
