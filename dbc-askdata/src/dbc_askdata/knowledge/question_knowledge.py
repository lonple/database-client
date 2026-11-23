from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskKnowledgeBinding
from dbc_askdata.db.scope import find_connection, is_pg_style, normalize_scope
from dbc_askdata.graph.sql_tables import source_tables_from_draft

log = logging.getLogger(__name__)


def _bare_table(key: str) -> str:
    return key.rsplit(".", 1)[-1] if key else ""


def _schema_of(key: str) -> str | None:
    if "." in key:
        return key.rsplit(".", 1)[0]
    return None


async def build_question_body_and_tables(
    sqlwork: SqlworkClient,
    *,
    workspace_id: int,
    connection_id: int,
    database: str | None,
    schema: str | None,
    draft_or_nodes: dict[str, Any],
    question: str,
) -> tuple[str, list[dict[str, str]]]:
    """
    解析 SQL 涉表 → sqlwork 补全列信息 → 组装问句文档正文（原始信息不压缩）。
    压缩由 ada-memory 建库/切片流程处理。
    """
    keys = sorted(source_tables_from_draft(draft_or_nodes, default_schema=schema))
    involved: list[dict[str, str]] = []
    sections: list[str] = [f"# 用户问题\n\n{question.strip()}\n", "# 涉表\n"]
    for key in keys:
        table = _bare_table(key)
        sch = _schema_of(key) or schema
        if not table:
            continue
        comment = ""
        try:
            # 尝试用 tables 列表取 comment
            listed = await sqlwork.list_tables(
                workspace_id,
                connection_id,
                database=database,
                schema=sch,
                keyword=table,
                page=1,
                size=20,
            )
            for it in listed.get("items") or []:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or it.get("tableName") or "").strip()
                if name.lower() == table.lower():
                    comment = str(it.get("comment") or it.get("remarks") or "").strip()
                    break
        except Exception:
            log.warning("拉取表注释失败 table=%s", table, exc_info=True)
        cols: list[dict[str, Any]] = []
        try:
            cols = await sqlwork.list_columns(
                workspace_id,
                connection_id,
                table=table,
                database=database,
                schema=sch,
            )
        except Exception:
            log.warning("拉取列失败 table=%s", table, exc_info=True)
        involved.append({"name": table, "description": comment})
        col_lines: list[str] = []
        for c in cols or []:
            if not isinstance(c, dict):
                continue
            cname = str(c.get("name") or c.get("columnName") or "").strip()
            if not cname:
                continue
            ctype = str(c.get("dataType") or c.get("type") or "").strip()
            ccomment = str(c.get("comment") or c.get("remarks") or "").strip()
            col_lines.append(f"- {cname} | {ctype} | {ccomment}")
        sections.append(f"## {table}\n\n表描述：{comment or '（无）'}\n\n### 字段\n")
        sections.append("\n".join(col_lines) if col_lines else "（无列信息）")
        sections.append("")
    body = "\n".join(sections).strip()
    return body, involved


async def create_question_knowledge_draft(
    *,
    settings: Settings,
    session: AsyncSession,
    sqlwork: SqlworkClient,
    user_id: int,
    workspace_id: int,
    connection_id: int,
    database: str | None,
    schema: str | None,
    question: str,
    nodes_json: dict[str, Any],
) -> dict[str, Any]:
    """
    写入问句知识草稿（不发布）：标题=问句，正文=涉表原始信息；索引 category=QUESTION。
    """
    q = (question or "").strip()
    if not q:
        raise ValueError("问句为空")
    body, involved = await build_question_body_and_tables(
        sqlwork,
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        draft_or_nodes=nodes_json,
        question=q,
    )
    if not involved:
        return {"skipped": True, "reason": "no_tables"}

    conns = await sqlwork.list_connections(workspace_id)
    conn = find_connection(conns, connection_id)
    db_type = str((conn or {}).get("dbType") or (conn or {}).get("db_type") or "")
    database_n, schema_n = normalize_scope(
        label="问句知识",
        connection_id=connection_id,
        database=database,
        schema=schema,
        db_type=db_type,
    )
    if not is_pg_style(db_type):
        schema_n = None

    client = AdaMemoryClient(settings)
    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    summary = f"问数已验证样本；涉表：{', '.join(t['name'] for t in involved)}"[:2000]
    category_id = await client.category_id("QUESTION")
    doc = await client.create_document(
        {
            "title": q[:256],
            "summary": summary,
            "productName": product,
            "orientation": "BOTH",
            "body": body,
            "sourceType": "QUESTION",
            "categoryId": category_id,
            "createdBy": str(user_id),
            "updateMode": "CREATE",
        }
    )
    doc_id = int(doc.get("id"))
    try:
        await client.suggest_slices(doc_id, force=True, orientation="BOTH")
    except Exception:
        log.warning("问句知识 suggest_slices 失败 doc_id=%s（草稿仍保留）", doc_id, exc_info=True)
    return {
        "documentId": doc_id,
        "involvedTables": involved,
        "published": False,
    }
