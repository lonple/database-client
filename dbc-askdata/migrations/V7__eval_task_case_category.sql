-- 任务用例外键快照分类，便于按类汇总通过率（不依赖用例日后改类）
ALTER TABLE askdata.eval_task_case
    ADD COLUMN IF NOT EXISTS category VARCHAR(64);

UPDATE askdata.eval_task_case tc
SET category = c.category
FROM askdata.eval_case c
WHERE tc.case_id = c.id
  AND (tc.category IS NULL OR btrim(tc.category) = '');

CREATE INDEX IF NOT EXISTS idx_eval_task_case_category
    ON askdata.eval_task_case(task_id, category);
