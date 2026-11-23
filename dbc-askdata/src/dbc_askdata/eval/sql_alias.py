from __future__ import annotations

"""将 SELECT 别名还原为原始列名，便于测评结果按物理字段对齐。"""

import logging
from typing import Any

import sqlglot
from sqlglot import exp

log = logging.getLogger(__name__)


def _parse_last_select(sql: str, *, dialect: str = "postgres") -> exp.Select | None:
    text = (sql or "").strip()
    if not text:
        return None
    # 多语句取最后一条可解析的 SELECT（问数草稿常拼接多节点）
    chunks = [c.strip() for c in text.split(";") if c.strip()]
    if not chunks:
        chunks = [text]
    last_sel: exp.Select | None = None
    for chunk in chunks:
        try:
            tree = sqlglot.parse_one(chunk, read=dialect)
        except Exception:
            log.warning("sql 别名解析失败 chunk=%s", chunk[:120], exc_info=True)
            continue
        sel = _outer_select(tree)
        if sel is not None:
            last_sel = sel
    return last_sel


def _outer_select(tree: exp.Expression) -> exp.Select | None:
    if isinstance(tree, exp.Select):
        return tree
    if isinstance(tree, exp.Subquery) and isinstance(tree.this, exp.Select):
        return tree.this
    if isinstance(tree, exp.With) and isinstance(tree.this, exp.Select):
        return tree.this
    if isinstance(tree, exp.Union):
        return _outer_select(tree.this) if tree.this else None
    return None


def _column_base_name(node: exp.Expression | None) -> str | None:
    """取投影表达式的原始字段名；非列引用（聚合/表达式）返回 None。"""
    if node is None:
        return None
    if isinstance(node, exp.Column):
        name = (node.name or "").strip()
        return name or None
    # CAST(col AS typ) / ::cast
    if isinstance(node, exp.Cast):
        return _column_base_name(node.this)
    return None


def _unwrap_cast(node: exp.Expression | None) -> exp.Expression | None:
    cur = node
    while isinstance(cur, exp.Cast):
        cur = cur.this
    return cur


def _is_count_expr(node: exp.Expression | None) -> bool:
    """COUNT(*) / COUNT(col) / COUNT(DISTINCT …)，可外裹 CAST。"""
    inner = _unwrap_cast(node)
    return isinstance(inner, exp.Count)


def _first_column_name(node: exp.Expression | None) -> str | None:
    """从表达式树中取第一个列引用名（用于 SUM(col) / COALESCE(SUM(col),0)）。"""
    if node is None:
        return None
    if isinstance(node, exp.Column):
        name = (node.name or "").strip()
        return name or None
    # 优先当前节点的 this（Sum/Cast/Coalesce 主体）
    for child in node.iter_expressions():
        found = _first_column_name(child)
        if found:
            return found
    return None


def _resolve_projection_source(node: exp.Expression | None) -> str | None:
    """投影表达式 → 规范/原始列名。

    - COUNT(...)：固定 cnt（与别名、计数字段无关）
    - 其它：还原为表达式内原始字段名（如 SUM(total_amount) AS x → total_amount）
    """
    if node is None:
        return None
    if _is_count_expr(node):
        return "cnt"
    base = _column_base_name(node)
    if base:
        return base.lower()
    # SUM/AVG/… / COALESCE(SUM(...), 0) 等：取内部列
    col = _first_column_name(node)
    if col:
        return col.lower()
    return None


def _proj_output_name(expr: exp.Expression) -> str | None:
    if isinstance(expr, exp.Alias):
        return (expr.alias or "").strip() or None
    if isinstance(expr, exp.Column):
        return (expr.name or "").strip() or None
    if _is_count_expr(expr):
        return "count"
    # 无别名聚合时驱动可能用函数名；尽量用源列，否则用函数名小写
    src = _resolve_projection_source(expr)
    return src


def select_alias_to_source(sql: str, *, dialect: str = "postgres") -> dict[str, str]:
    """解析最外层 SELECT：输出别名/列名 → 原始/规范列名（小写）。

    - 列引用 / CAST(列)：还原为原始字段名
    - COUNT(...)[::cast][AS 任意别名]：统一为 cnt
    - SUM(col) / COALESCE(SUM(col), …)[AS 任意别名]：还原为 col
    """
    sel = _parse_last_select(sql, dialect=dialect)
    if sel is None:
        return {}
    out: dict[str, str] = {}
    for e in sel.expressions or []:
        if isinstance(e, exp.Star):
            continue
        if isinstance(e, exp.Column) and isinstance(getattr(e, "this", None), exp.Star):
            continue

        if isinstance(e, exp.Alias):
            alias = (e.alias or "").strip()
            if not alias:
                continue
            src = _resolve_projection_source(e.this)
            if src:
                out[alias.lower()] = src
            continue

        src = _resolve_projection_source(e)
        if src:
            name = _proj_output_name(e) or src
            out[name.lower()] = src
            continue

        base = _column_base_name(e)
        if base:
            out[base.lower()] = base.lower()
    return out


def normalize_count_aliases_in_sql(sql: str, *, dialect: str = "postgres") -> str:
    """将最外层 SELECT 中 COUNT(...) 投影统一为 AS cnt（测评约定）。

    同步改写 ORDER BY 等处对旧别名的裸引用。解析失败则原样返回。
    """
    text = (sql or "").strip()
    if not text:
        return sql or ""
    try:
        tree = sqlglot.parse_one(text, read=dialect)
    except Exception:
        log.warning("COUNT 别名规范化解析失败", exc_info=True)
        return text
    sel = _outer_select(tree)
    if sel is None:
        return text

    renamed: dict[str, str] = {}
    new_exprs: list[exp.Expression] = []
    changed = False
    for e in list(sel.expressions or []):
        if isinstance(e, exp.Alias) and _is_count_expr(e.this):
            old = (e.alias or "").strip()
            if old.lower() != "cnt":
                if old:
                    renamed[old.lower()] = old
                changed = True
                new_exprs.append(exp.alias_(e.this.copy(), "cnt"))
            else:
                new_exprs.append(e)
        elif _is_count_expr(e):
            changed = True
            new_exprs.append(exp.alias_(e.copy(), "cnt"))
        else:
            new_exprs.append(e)
    if not changed:
        return text

    sel.set("expressions", new_exprs)

    if renamed:
        for col in tree.find_all(exp.Column):
            name = (col.name or "").strip()
            if not name or name.lower() not in renamed:
                continue
            # 仅改无表前缀的别名引用（ORDER BY cnt）
            if col.args.get("table") or col.args.get("db"):
                continue
            col.set("this", exp.to_identifier("cnt"))

    try:
        return tree.sql(dialect=dialect)
    except Exception:
        log.warning("COUNT 别名规范化序列化失败", exc_info=True)
        return text

def normalize_draft_count_aliases(
    draft: dict[str, Any] | None,
    *,
    dialect: str = "postgres",
) -> dict[str, Any] | None:
    """对草稿各节点 SQL 做 COUNT→cnt 规范化（测评落库/执行前）。"""
    if not draft:
        return draft
    nodes = draft.get("nodes")
    if not isinstance(nodes, list):
        return draft
    out_nodes: list[Any] = []
    changed = False
    for n in nodes:
        if not isinstance(n, dict):
            out_nodes.append(n)
            continue
        sql = n.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            out_nodes.append(n)
            continue
        fixed = normalize_count_aliases_in_sql(sql, dialect=dialect)
        if fixed != sql:
            changed = True
            out_nodes.append({**n, "sql": fixed})
        else:
            out_nodes.append(n)
    if not changed:
        return draft
    return {**draft, "nodes": out_nodes}


def rewrite_result_columns_by_sql(
    result: dict[str, Any] | None,
    sql: str | None,
    *,
    dialect: str = "postgres",
) -> tuple[dict[str, Any] | None, list[str]]:
    """按 SQL 别名映射，把结果集列名从别名改为原始字段名。

    返回 (新结果, 转换说明如 dn->dept_name)。无法解析或无别名时原样返回。
    """
    if not result or not (sql or "").strip():
        return result, []
    mapping = select_alias_to_source(sql or "", dialect=dialect)
    if not mapping:
        return result, []

    cols = result.get("columns") or []
    new_cols: list[Any] = []
    notes: list[str] = []
    used_targets: set[str] = set()

    for c in cols:
        if isinstance(c, dict):
            name = str(c.get("name") or c.get("columnName") or "")
            rest = {k: v for k, v in c.items() if k not in ("name", "columnName")}
        else:
            name = str(c)
            rest = {}
        key = name.strip().lower()
        target = mapping.get(key)
        if target and target != key and target not in used_targets:
            notes.append(f"{key}->{target}")
            used_targets.add(target)
            if isinstance(c, dict):
                new_cols.append({**rest, "name": target})
            else:
                new_cols.append(target)
        else:
            if target:
                used_targets.add(target if target == key else key)
            if isinstance(c, dict):
                new_cols.append(c if "name" in c or "columnName" in c else {"name": name, **rest})
            else:
                new_cols.append(c)

    if not notes:
        return result, []
    out = dict(result)
    out["columns"] = new_cols
    return out, notes


def rewrite_required_columns_by_sql(
    spec: dict[str, Any] | None,
    sql: str | None,
    *,
    dialect: str = "postgres",
) -> tuple[dict[str, Any] | None, list[str]]:
    """把用例必须返回字段按期望 SQL 别名映射还原为原始/规范列名。

    读取顺序与比对一致：requiredColumns / required_columns / columns。
    例：必须列 amt，期望 SQL 为 coalesce(sum(total_amount),0) AS amt → total_amount。
    COUNT 别名仍统一为 cnt。
    """
    if not spec or not (sql or "").strip():
        return spec, []
    mapping = select_alias_to_source(sql or "", dialect=dialect)
    if not mapping:
        return spec, []

    key = next(
        (
            k
            for k in ("requiredColumns", "required_columns", "columns")
            if isinstance(spec.get(k), list) and spec.get(k)
        ),
        None,
    )
    if key is None:
        return spec, []

    new_cols: list[str] = []
    notes: list[str] = []
    seen: set[str] = set()
    used_targets: set[str] = set()
    for raw in spec.get(key) or []:
        name = str(raw).strip()
        src = name.lower()
        target = mapping.get(src)
        if target and target != src and target not in used_targets:
            notes.append(f"{src}->{target}")
            used_targets.add(target)
            chosen = target
        else:
            if target:
                used_targets.add(target if target == src else src)
            chosen = src
        if chosen and chosen not in seen:
            seen.add(chosen)
            new_cols.append(chosen)

    if not notes:
        return spec, []
    out = dict(spec)
    out[key] = new_cols
    return out, notes
