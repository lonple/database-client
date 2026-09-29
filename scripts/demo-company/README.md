# company 演示库（智能问数业务样例）

本地 PostgreSQL 库 `postgres` 下 schema **`company`**。

模拟一家 IT 公司约 3 年经营/人事/财务/销售数据，含空值与异常行，供问数联调。

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

## 规模参考（SEED=20260928）

| 实体 | 约量 |
|------|------|
| 员工 | ~165（含离职；期末在职约 130+） |
| 日考勤 | ~7.6 万 |
| 工资条 | ~4.2 千（36 个薪资月） |
| 报销 | ~1.7 千单 |
| 项目 / 销售订单 | 24 / 95 |

时间窗：`2023-10-01` ~ `2026-09-28`。
