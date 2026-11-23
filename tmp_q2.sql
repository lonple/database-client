SELECT tc.case_key, left(tc.ask_sql,200) AS ask_sql, w.nodes_json
FROM askdata.eval_task_case tc
LEFT JOIN askdata.ask_workflow w ON w.id = tc.workflow_id
WHERE tc.task_id=5 AND tc.case_key='TPL_GOV_B_007';
