-- SQL 示例知识分类：问数按分类拉取原文正文注入上下文（可不切片）
INSERT INTO knowledge.t_knowledge_category (name, code, path, sort_no)
SELECT 'SQL示例', 'SQL_EX', '/SQL_EX', 40
WHERE NOT EXISTS (
    SELECT 1 FROM knowledge.t_knowledge_category WHERE code = 'SQL_EX'
);

UPDATE knowledge.t_knowledge_category
SET path = '/' || id::text
WHERE code = 'SQL_EX'
  AND (path IS NULL OR path = '/SQL_EX' OR path !~ '^/[0-9]+(/[0-9]+)*$');
