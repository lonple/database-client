SELECT
  CASE
    WHEN ask_error LIKE '%HITL%' THEN 'HITL_EXHAUSTED'
    WHEN ask_error LIKE '%project_id%' THEN 'SQL_project_id'
    WHEN ask_error LIKE '%d.name%' OR ask_error LIKE '%column \"name\"%' OR ask_error LIKE '%column %name% does not exist%' THEN 'SQL_dept_name'
    ELSE 'OTHER'
  END AS fail_kind,
  count(*)
FROM askdata.eval_task_case
WHERE task_id=5 AND status='ASK_FAILED'
GROUP BY 1 ORDER BY 2 DESC;
