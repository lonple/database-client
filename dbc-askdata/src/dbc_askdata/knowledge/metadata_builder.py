from __future__ import annotations

from typing import Any

from dbc_askdata.clients.sqlwork import SqlworkClient


def _col_line(col: dict[str, Any]) -> str:
    name = col.get("name") or col.get("columnName") or "?"
    ctype = col.get("type") or col.get("dataType") or col.get("typeName") or ""
    comment = (col.get("comment") or col.get("remarks") or "").strip()
    nullable = col.get("nullable")
    null_s = ""
    if nullable is False:
        null_s = " NOT NULL"
    elif nullable is True:
        null_s = " NULL"
    remark = f"  -- {comment}" if comment else ""
    return f"- `{name}` {ctype}{null_s}{remark}"


def _table_title(table: dict[str, Any], database: str, schema: str | None) -> str:
    name = table.get("name") or table.get("tableName") or "unknown"
    if schema:
        return f"{database}.{schema}.{name}"
    return f"{database}.{name}"


def _table_summary(table: dict[str, Any], database: str, schema: str | None) -> str:
    name = table.get("name") or table.get("tableName") or "unknown"
    comment = (table.get("comment") or table.get("remarks") or "").strip()
    scope = f"{database}.{schema}" if schema else database
    if comment:
        return f"{scope} 表 `{name}`：{comment}"
    return f"{scope} 表 `{name}` 的结构元数据"


async def build_metadata_knowledge(
    sqlwork: SqlworkClient,
    *,
    workspace_id: int,
    connection_id: int,
    database: str,
    schema: str | None,
    connection_name: str | None = None,
    db_type: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """拉取库表列结构，生成原文 Markdown + 按表切片（每片含 title/summary/body）。"""
    tables: list[dict[str, Any]] = []
    page = 1
    while True:
        page_data = await sqlwork.list_tables(
            workspace_id,
            connection_id,
            database=database,
            schema=schema,
            page=page,
            size=100,
        )
        items = page_data.get("items") or page_data.get("records") or []
        if isinstance(items, list):
            tables.extend(items)
        total = int(page_data.get("total") or 0)
        if not items or len(tables) >= total or len(items) < 100:
            break
        page += 1

    scope_label = f"{database}.{schema}" if schema else database
    header_lines = [
        f"# 数据库结构：{scope_label}",
        "",
        f"- 连接：{connection_name or connection_id}",
        f"- 类型：{db_type or '-'}",
        f"- 库：{database}",
    ]
    if schema:
        header_lines.append(f"- 模式：{schema}")
    header_lines.extend(["", f"共 {len(tables)} 张表。", ""])

    slices: list[dict[str, Any]] = []
    body_parts: list[str] = ["\n".join(header_lines)]

    for idx, table in enumerate(tables):
        tname = table.get("name") or table.get("tableName")
        if not tname:
            continue
        cols = await sqlwork.list_columns(
            workspace_id,
            connection_id,
            table=str(tname),
            database=database,
            schema=schema,
        )
        title = _table_title(table, database, schema)
        summary = _table_summary(table, database, schema)
        comment = (table.get("comment") or table.get("remarks") or "").strip()
        section_lines = [
            f"## {title}",
            "",
        ]
        if comment:
            section_lines.append(f"> {comment}")
            section_lines.append("")
        section_lines.append("### 列")
        section_lines.append("")
        if cols:
            for c in cols:
                section_lines.append(_col_line(c))
        else:
            section_lines.append("_无列信息_")
        section_lines.append("")
        section = "\n".join(section_lines)
        body_parts.append(section)
        slices.append(
            {
                "title": title,
                "summary": summary,
                "body": section,
                "orientation": "VERTICAL",
                "seqNo": idx + 1,
                "techTags": ["metadata", "table"],
            }
        )

    return "\n".join(body_parts).strip() + "\n", slices
