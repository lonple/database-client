# 测评用例配额（模板 IT 公司运维问数 v1）

> 已由 `gen_cases.py` 按 company_eval_v2 实库**元数据驱动**生成，见 [`cases/`](./cases/)。  
> **全表覆盖 + 归一化骨架≤2**：骨架按归一化 SQL 计（字面量/数字/DATE→占位），同 category 内 max≤2；`company` 约 200 表均须出现在有 `expect_sql` 的用例中。  
> 当前用例集已去掉模板治理（BOARD / 补全 / 拒答）。治理只保留手写 `cases/07_complex_govern.jsonl`（10 条）。生成器和导入器均不再写入 `MULTI_GOVERN_FILTER` / `MULTI_GOVERN_AGG`。

| category | 目标 | 实绩 | govern 划分 |
|----------|------|------|-------------|
| SINGLE_FILTER | 100 | 100（+脏口径样例） | — |
| MULTI_JOIN_FILTER | 100 | 100 | — |
| SINGLE_AGG | 100 | 100 | — |
| MULTI_JOIN_AGG | 100 | 100 | — |

## JSONL 字段（每行一用例）

```json
{
  "case_key": "TPL_SF_001",
  "scope": "TEMPLATE",
  "category": "SINGLE_FILTER",
  "govern_subtype": null,
  "question": "工号 E230005 入职是哪天？",
  "expect_sql": "SELECT emp_no, hire_date FROM company.hr_employee WHERE emp_no = 'E230005'",
  "compare_mode": "scalar",
  "compare_spec": {"columns": ["emp_no", "hire_date"]},
  "hitl_replies": null,
  "tags": ["hr", "point_lookup"]
}
```
