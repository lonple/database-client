from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskHitlCard, AskKnowledgeBinding
from dbc_askdata.graph.sql_tables import normalize_table_key, source_tables_from_draft
from dbc_askdata.knowledge.hitl_card import normalize_surface

log = logging.getLogger(__name__)

INTENT_SECTION = "## 人工确认·意图表映射"
FIELD_DICT_HEAD = "### 人工确认·字段字典"
_INTENT_LINE = re.compile(
    r"^-\s*`(?P<surface>[^`]+)`\s*→\s*`(?P<table>[^`]+)`(?:\s*\(x(?P<n>\d+)\))?\s*$"
)
_FIELD_LINE = re.compile(
    r"^-\s*`(?P<col>[^`]+)`:\s*`(?P<surface>[^`]+)`\s*→\s*`(?P<code>[^`]+)`(?:\s*\(x(?P<n>\d+)\))?\s*$"
)


def bare_table(name: str | None) -> str:
    if not name:
        return ""
    return str(name).rsplit(".", 1)[-1].strip().lower()


def _table_heading_candidates(table: str, database: str | None, schema: str | None) -> list[str]:
    t = (table or "").strip()
    if not t:
        return []
    bare = t.rsplit(".", 1)[-1]
    sch = (schema or "").strip()
    db = (database or "").strip()
    out: list[str] = []
    for h in (
        t,
        f"{db}.{sch}.{bare}" if db and sch else "",
        f"{db}.{bare}" if db else "",
        f"{sch}.{bare}" if sch else "",
        bare,
    ):
        if h and h not in out:
            out.append(h)
    return out


def merge_intent_mapping_body(
    body: str,
    *,
    surface: str,
    table: str,
) -> tuple[str, str]:
    """合并意图→表行。返回 (new_body, action=merged|conflict|appended|noop)。"""
    surf = normalize_surface(surface) or normalize_surface(table)
    tbl = (table or "").strip()
    if not surf or not tbl:
        return body or "", "noop"

    text = body or ""
    if INTENT_SECTION not in text:
        block = f"{INTENT_SECTION}\n\n- `{surf}` → `{tbl}`\n"
        if text.strip():
            return text.rstrip() + "\n\n" + block, "appended"
        return f"# 意图→表映射\n\n{block}", "appended"

    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == INTENT_SECTION)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") and i > start:
            end = i
            break

    section = lines[start:end]
    new_section: list[str] = []
    found = False
    action = "appended"
    for ln in section:
        m = _INTENT_LINE.match(ln.strip())
        if not m:
            new_section.append(ln)
            continue
        s_exist = normalize_surface(m.group("surface"))
        t_exist = m.group("table").strip()
        if s_exist != surf:
            new_section.append(ln)
            continue
        found = True
        if bare_table(t_exist) == bare_table(tbl) or t_exist.lower() == tbl.lower():
            n = int(m.group("n") or "1") + 1
            new_section.append(f"- `{surf}` → `{t_exist}` (x{n})")
            action = "merged"
        else:
            new_section.append(ln)
            new_section.append(f"- `{surf}` → `{tbl}`  <!-- CONFLICT with `{t_exist}` -->")
            action = "conflict"
    if not found:
        # 插到 section 末尾空行前
        insert_at = len(new_section)
        while insert_at > 1 and not new_section[insert_at - 1].strip():
            insert_at -= 1
        new_section.insert(insert_at, f"- `{surf}` → `{tbl}`")
        action = "appended"

    merged_lines = lines[:start] + new_section + lines[end:]
    return "\n".join(merged_lines).rstrip() + "\n", action


def merge_field_dict_into_metadata_body(
    body: str,
    *,
    table: str,
    column: str | None,
    surface: str,
    code: str,
    database: str | None = None,
    schema: str | None = None,
) -> tuple[str, str]:
    """在 METADATA 文中定位表章节，合并字段字典行。"""
    col = (column or "").strip() or "_"
    surf = normalize_surface(surface) or normalize_surface(code)
    code_s = (code or "").strip()
    if not surf or not code_s:
        return body or "", "noop"

    text = body or ""
    headings = _table_heading_candidates(table, database, schema)
    lines = text.splitlines()
    start = -1
    matched_heading = ""
    for i, ln in enumerate(lines):
        if not ln.startswith("## "):
            continue
        title = ln[3:].strip()
        for h in headings:
            if title.lower() == h.lower() or title.lower().endswith("." + bare_table(h)):
                start = i
                matched_heading = title
                break
        if start >= 0:
            break

    if start < 0:
        # 新建表章节
        section = [
            f"## {headings[0] if headings else table}",
            "",
            FIELD_DICT_HEAD,
            "",
            f"- `{col}`: `{surf}` → `{code_s}`",
            "",
        ]
        if text.strip():
            return text.rstrip() + "\n\n" + "\n".join(section), "appended_section"
        return "# 数据库结构\n\n" + "\n".join(section), "appended_section"

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    section = lines[start:end]

    # 找/建 字段字典小节
    dict_idx = next((i for i, ln in enumerate(section) if ln.strip() == FIELD_DICT_HEAD), -1)
    action = "appended"
    if dict_idx < 0:
        section = list(section)
        # 去掉尾部空行再追加
        while section and not section[-1].strip():
            section.pop()
        section.extend(["", FIELD_DICT_HEAD, "", f"- `{col}`: `{surf}` → `{code_s}`", ""])
        action = "appended"
    else:
        dict_end = len(section)
        for i in range(dict_idx + 1, len(section)):
            if section[i].startswith("### ") or section[i].startswith("## "):
                dict_end = i
                break
        new_dict: list[str] = []
        found = False
        for ln in section[dict_idx:dict_end]:
            m = _FIELD_LINE.match(ln.strip())
            if not m:
                new_dict.append(ln)
                continue
            if normalize_surface(m.group("col")) != normalize_surface(col):
                new_dict.append(ln)
                continue
            if normalize_surface(m.group("surface")) != surf:
                new_dict.append(ln)
                continue
            found = True
            exist_code = m.group("code").strip()
            if exist_code == code_s:
                n = int(m.group("n") or "1") + 1
                new_dict.append(f"- `{col}`: `{surf}` → `{code_s}` (x{n})")
                action = "merged"
            else:
                new_dict.append(ln)
                new_dict.append(
                    f"- `{col}`: `{surf}` → `{code_s}`  <!-- CONFLICT with `{exist_code}` -->"
                )
                action = "conflict"
        if not found:
            insert_at = len(new_dict)
            while insert_at > 1 and not new_dict[insert_at - 1].strip():
                insert_at -= 1
            new_dict.insert(insert_at, f"- `{col}`: `{surf}` → `{code_s}`")
            action = "appended"
        section = section[:dict_idx] + new_dict + section[dict_end:]

    merged = lines[:start] + section + lines[end:]
    return "\n".join(merged).rstrip() + "\n", action


async def _find_binding(
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    category: str,
) -> AskKnowledgeBinding | None:
    stmt = select(AskKnowledgeBinding).where(
        AskKnowledgeBinding.deleted.is_(False),
        AskKnowledgeBinding.knowledge_category == category,
        AskKnowledgeBinding.connection_id == int(connection_id),
        AskKnowledgeBinding.database_name == (database or "").strip(),
    )
    schema_s = (schema or "").strip()
    if schema_s:
        stmt = stmt.where(AskKnowledgeBinding.schema_name == schema_s)
    else:
        stmt = stmt.where(
            (AskKnowledgeBinding.schema_name.is_(None)) | (AskKnowledgeBinding.schema_name == "")
        )
    stmt = stmt.order_by(AskKnowledgeBinding.id.desc()).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _ensure_editable_doc(
    client: AdaMemoryClient,
    *,
    doc_id: int,
) -> tuple[int, dict[str, Any]]:
    """已发布则 start-update 出草稿；草稿直接返回。"""
    doc = await client.get_document(doc_id)
    status = str(doc.get("status") or "").upper()
    if status == "PUBLISHED":
        draft = await client.start_update(doc_id, update_mode="REPLACE_DOCUMENT")
        return int(draft["id"]), draft
    return int(doc_id), doc


async def _write_body_and_reslice(
    client: AdaMemoryClient,
    *,
    doc_id: int,
    body: str,
    summary: str | None = None,
) -> None:
    payload: dict[str, Any] = {"body": body}
    if summary:
        payload["summary"] = summary[:2000]
    await client.update_document(doc_id, payload)
    try:
        await client.suggest_slices(doc_id, force=True, orientation="BOTH")
    except Exception:
        log.warning("归并后 suggest_slices 失败 doc_id=%s", doc_id, exc_info=True)


async def _promote_table_card(
    session: AsyncSession,
    client: AdaMemoryClient,
    settings: Settings,
    card: AskHitlCard,
    *,
    user_id: int,
) -> dict[str, Any]:
    table = (card.target_table or card.target_value or "").strip()
    surface = (card.surface or card.question or table).strip()
    if not table:
        return {"ok": False, "action": "skip", "reason": "no_table"}

    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    binding = await _find_binding(
        session,
        connection_id=card.connection_id,
        database=card.database_name,
        schema=card.schema_name,
        category="INTENT_TABLE",
    )
    if binding is None:
        category_id = await client.ensure_category("INTENT_TABLE", name="意图表映射")
        scope = ".".join(
            x for x in (card.database_name, card.schema_name) if (x or "").strip()
        ) or str(card.connection_id)
        body = f"# 意图→表映射（{scope}）\n\n"
        body, action = merge_intent_mapping_body(body, surface=surface, table=table)
        doc = await client.create_document(
            {
                "title": f"意图表映射·{scope}"[:256],
                "summary": f"问数 HITL 确认的意图→物理表映射（{scope}）"[:2000],
                "productName": product,
                "orientation": "BOTH",
                "body": body,
                "sourceType": "HITL_INTENT",
                "categoryId": category_id,
                "createdBy": str(user_id),
                "updateMode": "CREATE",
            }
        )
        doc_id = int(doc["id"])
        try:
            await client.suggest_slices(doc_id, force=True, orientation="BOTH")
        except Exception:
            log.warning("INTENT_TABLE suggest_slices 失败 doc_id=%s", doc_id, exc_info=True)
        binding = AskKnowledgeBinding(
            name=f"意图表映射·{scope}"[:128],
            workspace_id=None,
            connection_id=card.connection_id,
            database_name=card.database_name,
            schema_name=card.schema_name,
            document_id=doc_id,
            document_name=str(doc.get("title") or "")[:256],
            knowledge_category="INTENT_TABLE",
            involved_tables=[{"name": bare_table(table), "description": surface}],
            remark="auto from HITL promote",
            owner_user_id=user_id,
        )
        session.add(binding)
        await session.commit()
        return {
            "ok": True,
            "action": action,
            "documentId": doc_id,
            "created": True,
            "conflict": action == "conflict",
        }

    edit_id, _doc = await _ensure_editable_doc(client, doc_id=int(binding.document_id))
    detail = await client.get_document(edit_id)
    old_body = str(detail.get("body") or "")
    new_body, action = merge_intent_mapping_body(old_body, surface=surface, table=table)
    await _write_body_and_reslice(client, doc_id=edit_id, body=new_body)
    return {
        "ok": True,
        "action": action,
        "documentId": edit_id,
        "sourceDocumentId": int(binding.document_id),
        "created": False,
        "conflict": action == "conflict",
    }


async def _promote_field_card(
    session: AsyncSession,
    client: AdaMemoryClient,
    card: AskHitlCard,
    *,
    draft_tables: set[str],
) -> dict[str, Any]:
    table = (card.target_table or "").strip()
    if not table:
        # 用最终草稿涉表兜底
        if len(draft_tables) == 1:
            table = next(iter(draft_tables))
        elif draft_tables:
            # 优先上下文表
            payload = card.payload if isinstance(card.payload, dict) else {}
            ctx = payload.get("contextTables") or []
            for c in ctx:
                key = normalize_table_key(str(c), default_schema=card.schema_name)
                if key in draft_tables or bare_table(key) in {bare_table(t) for t in draft_tables}:
                    table = str(c)
                    break
            if not table:
                table = next(iter(draft_tables))
    if not table:
        return {"ok": False, "action": "skip", "reason": "no_table"}

    code = (card.target_value or "").strip()
    if card.kind == "COLUMN":
        column = (card.target_column or card.target_value or "").strip()
        code = column
        surface = (card.surface or card.question or column).strip()
    else:
        column = (card.target_column or "").strip() or None
        surface = (card.surface or card.question or code).strip()
    if not code:
        return {"ok": False, "action": "skip", "reason": "no_value"}

    binding = await _find_binding(
        session,
        connection_id=card.connection_id,
        database=card.database_name,
        schema=card.schema_name,
        category="METADATA",
    )
    if binding is None:
        return {"ok": False, "action": "skip", "reason": "no_metadata_binding"}

    edit_id, _doc = await _ensure_editable_doc(client, doc_id=int(binding.document_id))
    detail = await client.get_document(edit_id)
    old_body = str(detail.get("body") or "")
    new_body, action = merge_field_dict_into_metadata_body(
        old_body,
        table=table,
        column=column,
        surface=surface,
        code=code,
        database=card.database_name,
        schema=card.schema_name,
    )
    await _write_body_and_reslice(client, doc_id=edit_id, body=new_body)
    return {
        "ok": True,
        "action": action,
        "documentId": edit_id,
        "sourceDocumentId": int(binding.document_id),
        "table": table,
        "conflict": action == "conflict",
    }


async def promote_session_hitl_cards(
    session: AsyncSession,
    *,
    settings: Settings,
    user_id: int,
    session_id: int,
    nodes_json: dict[str, Any] | None,
    default_schema: str | None = None,
) -> dict[str, Any]:
    """有用/记忆时：将会话内 PENDING 卡片归并进知识库。"""
    from dbc_askdata.knowledge.hitl_card import list_pending_cards

    cards = await list_pending_cards(session, session_id=session_id)
    if not cards:
        return {"promoted": 0, "conflict": 0, "skipped": 0, "items": []}

    draft_tables = source_tables_from_draft(nodes_json, default_schema=default_schema)
    client = AdaMemoryClient(settings)
    items: list[dict[str, Any]] = []
    promoted = conflict = skipped = 0

    for card in cards:
        try:
            if card.kind == "TABLE":
                # 最终 SQL 未用该表则跳过，防脏映射
                tbl = bare_table(card.target_table or card.target_value)
                if draft_tables and tbl and tbl not in {bare_table(t) for t in draft_tables}:
                    card.status = "SKIPPED"
                    card.promote_meta = {"reason": "table_not_in_final_draft", "draftTables": list(draft_tables)}
                    skipped += 1
                    items.append({"cardId": card.id, "kind": card.kind, "status": "SKIPPED"})
                    continue
                result = await _promote_table_card(
                    session, client, settings, card, user_id=user_id
                )
            elif card.kind in ("COLUMN", "EQ_LITERAL"):
                result = await _promote_field_card(
                    session, client, card, draft_tables=draft_tables
                )
            else:
                card.status = "SKIPPED"
                card.promote_meta = {"reason": "kind_not_supported"}
                skipped += 1
                items.append({"cardId": card.id, "kind": card.kind, "status": "SKIPPED"})
                continue

            if not result.get("ok"):
                card.status = "SKIPPED"
                card.promote_meta = result
                skipped += 1
                items.append({"cardId": card.id, "kind": card.kind, "status": "SKIPPED", **result})
                continue

            if result.get("conflict"):
                card.status = "CONFLICT"
                conflict += 1
            else:
                card.status = "PROMOTED"
                promoted += 1
            card.promoted_at = datetime.now(timezone.utc)
            card.promote_meta = result
            items.append({"cardId": card.id, "kind": card.kind, "status": card.status, **result})
        except Exception as ex:
            log.warning("HITL 卡片归并失败 card_id=%s", card.id, exc_info=True)
            card.status = "SKIPPED"
            card.promote_meta = {"reason": "error", "error": str(ex)[:500]}
            skipped += 1
            items.append({"cardId": card.id, "kind": card.kind, "status": "SKIPPED", "error": str(ex)[:200]})

    await session.commit()
    return {
        "promoted": promoted,
        "conflict": conflict,
        "skipped": skipped,
        "items": items,
    }
