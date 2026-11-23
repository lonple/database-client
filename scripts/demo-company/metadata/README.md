# company 库元数据

**唯一完整表结构文档**：[`db-structure.md`](./db-structure.md)

- 约 200 张表；每表四段：`## 英文表名` → 中文用途 → 字段一行摘要（`col 类型 说明|…`）→ 完整字段表
- 核心表枚举在字段说明中写 `key`=中文含义；文末含全量外键

辅助产物（非重复结构文档）：

- [`table-relations.md`](./table-relations.md) — 外键按子表分组的可读版（含域统计）
- [`table-relations.import.md`](./table-relations.import.md) — **可导入**库表关系 MD（问数「库表关系」页上传）
- [`extended_catalog.json`](./extended_catalog.json) — 扩展表中文目录（生成 `db-structure.md` 时合并）

说明：

- 核心表说明写在 `gen_db_structure_doc.py` 的 `TABLE_DESC` / `COL_DESC`；枚举字段须写明 `key`=中文含义。
- 扩展表以 catalog/库注释为准。
- 外键以 PostgreSQL 实际 FOREIGN KEY 为准。
- 导入 MD：页面「导入关系 MD」→ `POST /dbc-graph/api/graphs/import-md`；推荐 `table-relations.import.md`（也兼容 `table-relations.md` 表格）。

重生：

```powershell
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\gen_extended_schema.py
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\metadata\gen_db_structure_doc.py
.\dbc-askdata\.venv\Scripts\python.exe .\scripts\demo-company\metadata\export_table_relations.py
python .\scripts\demo-company\metadata\gen_table_relations_import_md.py
```
