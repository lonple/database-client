SELECT tc.case_key, tc.status, left(tc.ask_error,100) AS err,
  string_agg(s.kind||':'||s.name||':'||s.status, ' | ' ORDER BY s.id) AS spans
FROM askdata.eval_task_case tc
JOIN askdata.ask_llm_span s ON s.trace_id = tc.trace_id
WHERE tc.task_id=5 AND tc.case_key IN ('TPL_GOV_B_007','TPL_GOV_B_011','TPL_GOV_B_017','TPL_GOV_B_021')
GROUP BY tc.case_key, tc.status, tc.ask_error
ORDER BY tc.case_key;
