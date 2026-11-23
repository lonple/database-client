-- 问句知识 category=QUESTION；放宽 ask_knowledge 分类约束（V5 仅 GENERAL|METADATA）

ALTER TABLE askdata.ask_knowledge
    DROP CONSTRAINT IF EXISTS ck_ask_knowledge_category;

ALTER TABLE askdata.ask_knowledge
    ADD CONSTRAINT ck_ask_knowledge_category
    CHECK (knowledge_category IN ('GENERAL', 'METADATA', 'QUESTION'));

CREATE INDEX IF NOT EXISTS idx_ask_knowledge_question_scope
    ON askdata.ask_knowledge(connection_id, database_name, schema_name)
    WHERE deleted = FALSE AND knowledge_category = 'QUESTION';

COMMENT ON COLUMN askdata.ask_knowledge.knowledge_category IS 'GENERAL | METADATA | QUESTION';
