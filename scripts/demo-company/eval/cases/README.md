# 测评用例（模板种子）

- 话术标准：[`../phrasing-guide.md`](../phrasing-guide.md)
- 出题口径：[`../answer-key-notes.md`](../answer-key-notes.md)
- 配额：[`../quota.md`](../quota.md)
- 生成/校验：[`../gen_cases.py`](../gen_cases.py)（**全表覆盖 + 归一化 SQL 骨架≤2**；BOARD 的 `expect_sql` 用最简两表写法）

```powershell
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\eval\gen_cases.py
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\eval\gen_cases.py --validate-only
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\eval\check_dup.py
```

生成成功后会把 jsonl upsert 进 `askdata.eval_case`（`scope=TEMPLATE`，`template_id=company_eval_v2`）。

## 当前文件（company_eval_v2 / SEED=20261015）

| 文件 | 条数 | 说明 |
|------|------|------|
| `01_single_filter.jsonl` | 100+脏样例 | 单表条件（优先编码点查，覆盖优先） |
| `02_multi_join_filter.jsonl` | 100 | 多表 FK 关联条件 |
| `03_single_agg.jsonl` | 100 | 单表 count（补齐未覆盖表） |
| `04_multi_join_agg.jsonl` | 100 | 多表关联统计 |
| `07_complex_govern.jsonl` | 10 | 手写复杂治理：三表以上，分组 + 子查询，业务场景本身需要这么写 |
| `smoke.jsonl` | 手写烟雾 | 可保留作演示（导入时跳过） |

期望 SQL 已对本地 `company` 库执行校验。  
**表覆盖**：`company` schema 全部约 200 张表均至少出现在 1 条有 `expect_sql` 的用例中。

`MULTI_GOVERN_FILTER`、`MULTI_GOVERN_AGG` 已下线，生成器和导入器均不再写入这两类；保留 `COMPLEX_GOVERN`。服务启动时会清理旧用例及对应任务快照，并重算受影响任务指标。也可手动执行：

```powershell
.\dbc-askdata\.venv\Scripts\python.exe .\dbc-askdata\scripts\purge_retired_eval_categories.py --dsn postgresql+asyncpg://postgres:root@127.0.0.1:5432/postgres
```

**出题硬约束**（见 `phrasing-guide.md`）：
- 题面 / WHERE 过滤禁止内部自增 id、「主键 N」；无单号的事实表从关联主数据（工号、客户编码等）切入。
- 多表 / 治理类复杂题若设了 `requiredColumns`，题面须口语写明需要返回的字段。
