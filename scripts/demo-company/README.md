# company 测评库（company_eval_v2）

本地 PostgreSQL 库 `postgres` 下 schema **`company`**。

模拟一家 IT 公司约 3 年经营/人事/财务/销售数据，供智能问数**测评**与联调。  
库内**故意缺少**完整 COMMENT；表结构说明见 [`metadata/db-structure.md`](./metadata/db-structure.md)（交付风格；部分枚举有取值说明）。

## 连接

- Host: `127.0.0.1:5432`
- DB / User / Password: `postgres` / `postgres` / `root`
- Schema: `company`

## 一键重建

```powershell
cd e:\workspace\database-client
powershell -File .\scripts\demo-company\run.ps1
```

或分步：

```powershell
Get-Content -Raw -Encoding UTF8 .\scripts\demo-company\01_schema.sql | docker exec -i dbc-postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\seed_company.py
```

灌数较久（日考勤五十万级），请耐心等待。

## 规模实绩（SEED=20261002 · company_eval_v2 · 已灌库）

| 实体 | 实绩 |
|------|------|
| 员工 | **1000**（无 leave_date≈820；status=active≈837，含口径冲突） |
| 客户 / 项目 / 订单 | 300 / 150 / 1200 |
| 日考勤 | **496,955** |
| 工资条 / 报销 | 26,454 / 6,544 |
| 加班 / 工时填报 | 36,709 / 61,786 |

时间窗：`2023-10-01` ~ `2026-09-28`。

## 缺陷包（有意识，非纯随机）

| 包 | 意图 | 表现（示例） |
|----|------|----------------|
| A 空值 | 逼空值过滤 | 性别/城市/邮箱空；订单无客户；头金额空 |
| B 口径冲突 | 测「在职」等口径 | 有 `leave_date` 但 `employment_status=active`；报销头≠明细和 |
| C 需抽样 | 枚举未文档化 | 状态码无元数据说明；加班类型与日期可矛盾 |

出题人口径（不对模型开放）：[`eval/answer-key-notes.md`](./eval/answer-key-notes.md)。

## 相关设计

- [测评需求](../../doc/设计/需求/03-智能问数测评需求分析.md)
- [测评详设](../../doc/设计/详细设计/09-智能问数测评详细设计.md)
