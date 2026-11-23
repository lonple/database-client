# 共享策略片段（厂商无关）

各 `providers/<id>/prompts/*.md` 可通过 `{{include:policy/文件名.md}}` 引用本目录条款。

| 文件 | 用途 |
|------|------|
| `sql_core.md` | build 用的 SQL 纪律（选表、describe、码值、投影、分组等） |

输出契约写在各 provider 的 `build_system.md`：仅单节点 `QUERY`（优先 JOIN/子查询，尽量不用 WITH CTE）。多节点 GOVERN 路径已下线。
