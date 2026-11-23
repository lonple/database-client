from __future__ import annotations

"""明细查询语义校验：最外层等值 WHERE 列须投影；条件字面量须通过画像判定。

校验侧对每个 =/!=/IN/NOT IN 字面量调用 get_column_profile(condition_value=…)，
用 format/字典 action 判定：符合则放行，不符合则回灌大模型改 SQL。
字面量不必出现在 value_counts。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp

log = logging.getLogger(__name__)

_AGG_TYPES = (
    exp.Count,
    exp.Sum,
    exp.Avg,
    exp.Min,
    exp.Max,
    exp.GroupConcat,
)

@dataclass
class EqPredicate:
    """最外层 WHERE 中的等值谓词。"""

    column: str
    table: str | None = None
    """解析后的物理表名（经别名映射）。"""
    table_alias: str | None = None
    """SQL 中的表限定符（如 t2），补投影时优先用。"""
    literal: str | None = None
    literals: list[str] = field(default_factory=list)
    op: str = "="  # = | != | in | not_in


@dataclass
class SemanticIssue:
    code: str
    message: str
    missing_eq_cols: list[str] = field(default_factory=list)
    need_profile: list[dict[str, str]] = field(default_factory=list)
    bad_literals: list[dict[str, Any]] = field(default_factory=list)
    needs_hitl: bool = False


def _parse(sql: str, *, dialect: str = "postgres") -> exp.Expression | None:
    text = (sql or "").strip()
    if not text:
        return None
    try:
        return sqlglot.parse_one(text, read=dialect)
    except Exception:
        log.warning("semantic 解析失败", exc_info=True)
        return None


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


def is_detail_select(sql: str, *, dialect: str = "postgres") -> bool:
    """无最外层 GROUP BY、无投影聚合函数的明细查询。"""
    tree = _parse(sql, dialect=dialect)
    if tree is None:
        return False
    sel = _outer_select(tree)
    if sel is None:
        return False
    if sel.args.get("group") is not None:
        return False
    for proj in sel.expressions or []:
        if isinstance(proj, _AGG_TYPES):
            return False
        if isinstance(proj, exp.Alias) and isinstance(proj.this, _AGG_TYPES):
            return False
        # SELECT COUNT(*) AS c
        if proj.find(_AGG_TYPES) and not proj.find(exp.Window):
            # 窗口函数含聚合时仍算分析查询，按明细规则跳过更稳妥：有聚合即非明细
            # 简化：投影树中出现聚合 → 非明细
            for agg in proj.find_all(_AGG_TYPES):
                if agg.find_ancestor(exp.Window) is None:
                    return False
    return True


def _col_name(node: exp.Expression | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, exp.Column):
        return (node.name or "").strip() or None
    return None


def _col_table(node: exp.Expression | None) -> str | None:
    if isinstance(node, exp.Column):
        t = node.table
        return str(t).strip() if t else None
    return None


def _literal_str(node: exp.Expression | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, exp.Literal):
        return str(node.this) if node.this is not None else None
    if isinstance(node, exp.Boolean):
        return str(node.this)
    return None


def _from_alias_map(sel: exp.Select) -> dict[str, str]:
    """别名/表名 → 物理表名（无 schema）。"""
    out: dict[str, str] = {}
    for src in sel.find_all(exp.Table):
        parent_sel = src.find_ancestor(exp.Select)
        if parent_sel is not None and parent_sel is not sel:
            continue
        name = (src.name or "").strip()
        if not name:
            continue
        alias = (src.alias_or_name or name).strip()
        out[alias.lower()] = name
        out[name.lower()] = name
    return out


def _col_lit_sides(
    left: exp.Expression | None, right: exp.Expression | None
) -> tuple[exp.Column, exp.Expression] | None:
    """列 vs 字面量（或反过来）；列=列则跳过。"""
    if left is None or right is None:
        return None
    if _col_name(left) and _col_name(right):
        return None
    if _col_name(left) and isinstance(left, exp.Column):
        return left, right
    if _col_name(right) and isinstance(right, exp.Column):
        return right, left
    return None


def outer_eq_predicates(sql: str, *, dialect: str = "postgres") -> list[EqPredicate]:
    """提取最外层 WHERE 的全等集合谓词（= / != / IN / NOT IN）；不含范围、LIKE。"""
    tree = _parse(sql, dialect=dialect)
    if tree is None:
        return []
    sel = _outer_select(tree)
    if sel is None:
        return []
    where = sel.args.get("where")
    if not isinstance(where, exp.Where):
        return []
    alias_map = _from_alias_map(sel)
    preds: list[EqPredicate] = []

    def resolve_table(col: exp.Column) -> str | None:
        raw = _col_table(col)
        if raw:
            return alias_map.get(raw.lower(), raw)
        tables = {v for v in alias_map.values()}
        if len(tables) == 1:
            return next(iter(tables))
        return None

    def append_in(col: exp.Column, expressions: list[exp.Expression] | None, *, op: str) -> None:
        vals: list[str] = []
        for x in expressions or []:
            s = _literal_str(x)
            if s is None:
                return
            vals.append(s)
        if not vals:
            return
        preds.append(
            EqPredicate(
                column=col.name,
                table=resolve_table(col),
                table_alias=_col_table(col),
                literal=vals[0] if len(vals) == 1 else ",".join(vals),
                literals=list(vals),
                op=op,
            )
        )

    root = where.this
    if root is None:
        return []

    for node in root.walk():
        parent_select = node.find_ancestor(exp.Select)
        if parent_select is not None and parent_select is not sel:
            continue

        if isinstance(node, (exp.EQ, exp.NEQ)):
            sides = _col_lit_sides(node.left, node.right)
            if sides is None:
                continue
            col_expr, lit_expr = sides
            col_n = _col_name(col_expr)
            if not col_n:
                continue
            lit = _literal_str(lit_expr)
            if lit is None:
                continue
            preds.append(
                EqPredicate(
                    column=col_n,
                    table=resolve_table(col_expr),
                    table_alias=_col_table(col_expr),
                    literal=lit,
                    literals=[lit],
                    op="=" if isinstance(node, exp.EQ) else "!=",
                )
            )
        elif isinstance(node, exp.In) and isinstance(node.this, exp.Column):
            # postgres 的 NOT IN 常解析为 Not(In(...))；内层 In 在 walk 时也会出现，需跳过
            if isinstance(node.parent, exp.Not):
                continue
            is_not = bool(node.args.get("not"))
            append_in(node.this, list(node.expressions or []), op="not_in" if is_not else "in")
        elif isinstance(node, exp.Not) and isinstance(node.this, exp.In):
            inner = node.this
            if isinstance(inner.this, exp.Column):
                append_in(inner.this, list(inner.expressions or []), op="not_in")
    return preds


def select_output_columns(sql: str, *, dialect: str = "postgres") -> set[str] | None:
    """
    最外层 SELECT 输出列名集合（小写）。
    若含 * / table.* 返回 None 表示覆盖全部。
    """
    tree = _parse(sql, dialect=dialect)
    if tree is None:
        return set()
    sel = _outer_select(tree)
    if sel is None:
        return set()
    cols: set[str] = set()
    for e in sel.expressions or []:
        if isinstance(e, exp.Star):
            return None
        if isinstance(e, exp.Column) and isinstance(getattr(e, "this", None), exp.Star):
            return None
        name = None
        if isinstance(e, exp.Alias):
            name = e.alias
            base = _col_name(e.this)
            if base:
                cols.add(base.lower())
        else:
            name = _col_name(e)
        if name:
            cols.add(str(name).lower())
    return cols


def check_eq_projection(sql: str, *, dialect: str = "postgres") -> SemanticIssue | None:
    """明细查询：最外层等值 WHERE 列必须出现在 SELECT 投影中。"""
    if not is_detail_select(sql, dialect=dialect):
        return None
    preds = outer_eq_predicates(sql, dialect=dialect)
    if not preds:
        return None
    out = select_output_columns(sql, dialect=dialect)
    if out is None:
        return None
    missing: list[str] = []
    seen: set[str] = set()
    for p in preds:
        key = p.column.lower()
        if key in seen:
            continue
        seen.add(key)
        if key not in out:
            missing.append(p.column)
    if not missing:
        return None
    return SemanticIssue(
        code="EQ_COL_NOT_IN_SELECT",
        message=(
            "非聚合/无 GROUP BY 的明细查询中，最外层 WHERE 等值条件字段必须同时出现在 SELECT 投影中；"
            f"缺失列：{', '.join(missing)}。"
            "请将这些列加入最外层 SELECT（范围条件 LIKE/BETWEEN/</> 等不必投影）。"
        ),
        missing_eq_cols=missing,
    )


def ensure_eq_projection_in_select(
    sql: str, *, dialect: str = "postgres"
) -> tuple[str, list[str]]:
    """代码层补全：明细查询 WHERE 等值列若未进 SELECT，自动追加投影。

    返回 (新 SQL, 追加的列展示名列表)。无法解析或不适用时原样返回。
    """
    text = (sql or "").strip()
    if not text or not is_detail_select(text, dialect=dialect):
        return text, []
    tree = _parse(text, dialect=dialect)
    if tree is None:
        return text, []
    sel = _outer_select(tree)
    if sel is None:
        return text, []
    out = select_output_columns(text, dialect=dialect)
    if out is None:
        return text, []

    preds = outer_eq_predicates(text, dialect=dialect)
    if not preds:
        return text, []

    exprs = list(sel.expressions or [])
    added_labels: list[str] = []
    seen_missing: set[str] = set()
    for p in preds:
        key = (p.column or "").strip().lower()
        if not key or key in out or key in seen_missing:
            continue
        seen_missing.add(key)
        alias = (p.table_alias or "").strip() or None
        col = exp.column(p.column, table=alias) if alias else exp.column(p.column)
        exprs.append(col)
        out.add(key)
        added_labels.append(f"{alias}.{p.column}" if alias else p.column)

    if not added_labels:
        return text, []

    sel.set("expressions", exprs)
    try:
        rewritten = tree.sql(dialect=dialect)
    except Exception:
        log.warning("ensure_eq_projection sql 生成失败", exc_info=True)
        return text, []
    return rewritten, added_labels


def ensure_group_by_cols_in_select(
    sql: str, *, dialect: str = "postgres"
) -> tuple[str, list[str]]:
    """代码层补全：GROUP BY 中的普通列若未进 SELECT，自动追加投影。

    仅处理 Column 引用（可带表别名）。跳过：表达式、位置序号、非列节点。
    返回 (新 SQL, 追加的列展示名列表)。
    """
    text = (sql or "").strip()
    if not text:
        return text, []
    tree = _parse(text, dialect=dialect)
    if tree is None:
        return text, []
    sel = _outer_select(tree)
    if sel is None:
        return text, []
    group = sel.args.get("group")
    if group is None:
        return text, []
    out = select_output_columns(text, dialect=dialect)
    if out is None:
        return text, []

    group_exprs = list(getattr(group, "expressions", None) or [])
    if not group_exprs:
        return text, []

    exprs = list(sel.expressions or [])
    added_labels: list[str] = []
    seen: set[str] = set()
    for ge in group_exprs:
        # 位置序号 GROUP BY 1 → Literal，跳过
        if isinstance(ge, exp.Literal):
            continue
        col: exp.Column | None = None
        if isinstance(ge, exp.Column):
            col = ge
        elif isinstance(ge, exp.Alias) and isinstance(ge.this, exp.Column):
            # 少见：GROUP BY x AS ...
            col = ge.this
        else:
            # date_trunc(...) / lower(name) 等表达式：跳过
            continue
        name = (col.name or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in out or key in seen:
            continue
        seen.add(key)
        alias = (col.table or "").strip() or None
        new_col = exp.column(name, table=alias) if alias else exp.column(name)
        exprs.append(new_col)
        out.add(key)
        added_labels.append(f"{alias}.{name}" if alias else name)

    if not added_labels:
        return text, []

    sel.set("expressions", exprs)
    try:
        rewritten = tree.sql(dialect=dialect)
    except Exception:
        log.warning("ensure_group_by_cols sql 生成失败", exc_info=True)
        return text, []
    return rewritten, added_labels


def profile_cache_key(table: str | None, column: str, *, schema: str | None = None) -> str:
    parts: list[str] = []
    if schema:
        parts.append(schema.strip().lower())
    if table:
        parts.append(table.strip().lower())
    parts.append(column.strip().lower())
    return ".".join(parts)


def store_profile(
    profiles: dict[str, Any],
    *,
    table: str,
    column: str,
    schema: str | None,
    profile: dict[str, Any],
) -> None:
    keys = {
        profile_cache_key(table, column, schema=schema),
        profile_cache_key(table, column),
        column.strip().lower(),
    }
    packed = dict(profile)
    packed["table"] = table
    packed["column"] = column
    if schema:
        packed["schema"] = schema
    for k in keys:
        profiles[k] = packed


def lookup_profile(
    profiles: dict[str, Any],
    *,
    table: str | None,
    column: str,
    schema: str | None = None,
) -> dict[str, Any] | None:
    col = column.strip().lower()
    candidates = [
        profile_cache_key(table, column, schema=schema),
        profile_cache_key(table, column),
        col,
    ]
    for k in candidates:
        if k and k in profiles:
            return profiles[k]
    for k, v in profiles.items():
        if k == col or k.endswith(f".{col}"):
            if table is None or (table and table.lower() in k):
                return v
    return None


def _literal_like(old: exp.Expression, new_value: str) -> exp.Literal:
    """尽量保持原字面量形态（数字/字符串）。"""
    text = str(new_value)
    if isinstance(old, exp.Literal) and not getattr(old, "is_string", True):
        try:
            if "." in text:
                return exp.Literal.number(text)
            return exp.Literal.number(int(text))
        except ValueError:
            pass
    return exp.Literal.string(text)


def rewrite_use_key_literals(
    sql: str,
    replacements: list[dict[str, str]],
    *,
    dialect: str = "postgres",
) -> tuple[str, list[str]]:
    """将 WHERE 中指定列的字面量改写为字典 key。

    replacements 项：table / column / from / to。
    返回 (新 SQL, 改写说明列表)。无法解析时原样返回。
    """
    if not replacements:
        return (sql or "").strip(), []
    text = (sql or "").strip()
    tree = _parse(text, dialect=dialect)
    if tree is None:
        return text, []
    sel = _outer_select(tree)
    if sel is None:
        return text, []
    where = sel.args.get("where")
    if not isinstance(where, exp.Where) or where.this is None:
        return text, []

    alias_map = _from_alias_map(sel)

    def resolve_table(col: exp.Column) -> str:
        raw = _col_table(col)
        if raw:
            return alias_map.get(raw.lower(), raw)
        tables = {v for v in alias_map.values()}
        if len(tables) == 1:
            return next(iter(tables))
        return ""

    # (table_l, col_l, from_lit) -> to
    want: dict[tuple[str, str, str], str] = {}
    for item in replacements:
        table = (item.get("table") or "").strip().lower()
        column = (item.get("column") or "").strip().lower()
        frm = (item.get("from") or "").strip()
        to = (item.get("to") or "").strip()
        if not column or not frm or not to:
            continue
        want[(table, column, frm)] = to

    if not want:
        return text, []

    changed: list[str] = []

    def try_replace_lit(
        col: exp.Column, lit_expr: exp.Expression
    ) -> exp.Expression | None:
        col_n = (_col_name(col) or "").lower()
        if not col_n:
            return None
        table = resolve_table(col).lower()
        old = _literal_str(lit_expr)
        if old is None:
            return None
        to = want.get((table, col_n, old))
        if to is None and table:
            # 无表限定时 job.table 可能有值，AST 侧也可能解析到同表
            to = want.get(("", col_n, old))
        if to is None:
            # job 带了表名，AST 解析到同名物理表
            for (t, c, f), v in want.items():
                if c == col_n and f == old and (not t or t == table):
                    to = v
                    break
        if to is None or to == old:
            return None
        label = f"{table}.{col_n}" if table else col_n
        changed.append(f"{label}: {old!r} → {to!r}")
        return _literal_like(lit_expr, to)

    root = where.this
    for node in list(root.walk()):
        parent_select = node.find_ancestor(exp.Select)
        if parent_select is not None and parent_select is not sel:
            continue
        if isinstance(node, (exp.EQ, exp.NEQ)):
            sides = _col_lit_sides(node.left, node.right)
            if sides is None:
                continue
            col_expr, lit_expr = sides
            new_lit = try_replace_lit(col_expr, lit_expr)
            if new_lit is None:
                continue
            if node.left is lit_expr:
                node.set("this", new_lit)
            else:
                node.set("expression", new_lit)
        elif isinstance(node, exp.In) and isinstance(node.this, exp.Column):
            if isinstance(node.parent, exp.Not):
                continue
            exprs = list(node.expressions or [])
            new_exprs: list[exp.Expression] = []
            touched = False
            for x in exprs:
                repl = try_replace_lit(node.this, x)
                if repl is not None:
                    new_exprs.append(repl)
                    touched = True
                else:
                    new_exprs.append(x)
            if touched:
                node.set("expressions", new_exprs)
        elif isinstance(node, exp.Not) and isinstance(node.this, exp.In):
            inner = node.this
            if not isinstance(inner.this, exp.Column):
                continue
            exprs = list(inner.expressions or [])
            new_exprs = []
            touched = False
            for x in exprs:
                repl = try_replace_lit(inner.this, x)
                if repl is not None:
                    new_exprs.append(repl)
                    touched = True
                else:
                    new_exprs.append(x)
            if touched:
                inner.set("expressions", new_exprs)

    if not changed:
        return text, []
    try:
        return tree.sql(dialect=dialect), changed
    except Exception:
        log.warning("rewrite_use_key_literals sql 生成失败", exc_info=True)
        return text, []


def iter_eq_literal_jobs(
    sql: str, *, dialect: str = "postgres"
) -> list[dict[str, str]]:
    """展开 WHERE 全等集合条件为 (table, column, literal) 探测任务。"""
    jobs: list[dict[str, str]] = []
    seen: set[str] = set()
    for p in outer_eq_predicates(sql, dialect=dialect):
        col = (p.column or "").strip()
        if not col:
            continue
        table = (p.table or "").strip()
        lits = list(p.literals) if p.literals else ([p.literal] if p.literal else [])
        for lit in lits:
            text = (lit or "").strip()
            if not text:
                continue
            marker = f"{table.lower()}\0{col.lower()}\0{text}"
            if marker in seen:
                continue
            seen.add(marker)
            jobs.append({"table": table, "column": col, "literal": text})
    return jobs


def check_eq_literals_against_profiles(
    sql: str,
    profiles: dict[str, Any],
    *,
    dialect: str = "postgres",
    default_schema: str | None = None,
) -> SemanticIssue | None:
    """同步判定：用已缓存的画像 + accept_sql_literal。缺画像记入 need_profile。

    生产路径优先走 repair 里带 condition_value 的异步探测；本函数供单测与二次确认。
    """
    from dbc_askdata.verify.condition_match import accept_sql_literal

    jobs = iter_eq_literal_jobs(sql, dialect=dialect)
    if not jobs:
        return None

    need: list[dict[str, str]] = []
    bad: list[dict[str, Any]] = []
    for job in jobs:
        table = job["table"]
        column = job["column"]
        literal = job["literal"]
        prof = lookup_profile(
            profiles,
            table=table or None,
            column=column,
            schema=default_schema,
        )
        if prof is None:
            need.append({"table": table, "column": column, "literal": literal})
            continue
        verdict = accept_sql_literal(literal, prof)
        if verdict.get("ok"):
            continue
        bad.append(
            {
                "table": table,
                "column": column,
                "literal": literal,
                "action": verdict.get("action"),
                "message": verdict.get("message"),
            }
        )

    if need and not bad:
        labels = [
            f"{i['table']}.{i['column']}={i['literal']!r}"
            if i.get("table")
            else f"{i['column']}={i['literal']!r}"
            for i in need
        ]
        return SemanticIssue(
            code="EQ_LITERAL_NEED_PROFILE",
            message=(
                "WHERE 条件列尚无画像，需 get_column_profile(condition_value=字面量)："
                + ", ".join(labels)
            ),
            need_profile=[{"table": i["table"], "column": i["column"]} for i in need],
            bad_literals=need,
            needs_hitl=False,
        )
    if bad:
        parts = [
            f"{b.get('table') or '?'}.{b.get('column')}={b.get('literal')!r}"
            f"（{b.get('action')}）: {b.get('message')}"
            for b in bad
        ]
        return SemanticIssue(
            code="EQ_LITERAL_MISMATCH",
            message=(
                "WHERE 条件值未通过列画像/格式匹配，请按指摘改写 SQL 后重试：\n"
                + "\n".join(parts)
            ),
            need_profile=[],
            bad_literals=bad,
            needs_hitl=False,
        )
    if need:
        # 同时有缺画像与不匹配时，先报不匹配；缺画像留给异步拉取
        pass
    return None
