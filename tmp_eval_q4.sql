SELECT case_key, left(ask_sql,120), left(expect_sql,120)
FROM askdata.eval_task_case WHERE task_id=5 AND status='PASSED' ORDER BY case_key;
