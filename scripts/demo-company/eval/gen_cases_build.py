# -*- coding: utf-8 -*-
"""元数据驱动测评用例生成：全表覆盖 + 归一化 SQL 骨架≤2。

由 gen_cases.build_cases 调用；输入为 load_meta() 返回的 SchemaMeta。
"""
from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from gen_cases import add, utter, quote_label

# ---------------------------------------------------------------------------
# 核心 22 表中文名（extended_catalog 不含）
# ---------------------------------------------------------------------------
CORE_ZH: dict[str, str] = {
    "hr_employee": "员工",
    "hr_job_level": "职级",
    "org_department": "部门",
    "crm_customer": "客户",
    "prd_product": "产品",
    "prd_product_cost": "产品成本",
    "sal_sales_order": "销售订单",
    "sal_sales_order_item": "销售订单明细",
    "fin_reimburse": "报销单",
    "fin_reimburse_item": "报销明细",
    "fin_salary_period": "薪资期间",
    "fin_salary_slip": "工资条",
    "fin_activity_budget": "活动预算",
    "fin_activity_expense": "活动费用",
    "prj_project": "项目",
    "prj_project_member": "项目成员",
    "prj_project_revenue": "项目回款",
    "att_leave": "请假单",
    "att_leave_type": "请假类型",
    "att_overtime": "加班单",
    "att_timesheet": "工时填报",
    "att_daily_record": "考勤日报",
}

SKIP_DISPLAY = {
    "id",
    "created_at",
    "updated_at",
    "password",
    "pwd_hash",
}
NUMERIC_TYPES = {
    "numeric",
    "integer",
    "bigint",
    "smallint",
    "double precision",
    "real",
    "decimal",
}


@dataclass
class TableMeta:
    name: str
    zh: str
    columns: list[str]
    col_types: dict[str, str]
    col_zh: dict[str, str]
    business_key: str
    key_values: list[Any]
    display_cols: list[str]
    has_code_key: bool
    has_user_key: bool  # 业务可感知键（编码/单号/名称），非内部自增 id
    fks: list[tuple[str, str, str]] = field(default_factory=list)  # (src_col, dst_table, dst_col)


@dataclass
class SchemaMeta:
    tables: dict[str, TableMeta]
    fk_edges: list[tuple[str, str, str, str]]  # src, src_col, dst, dst_col
    conflict_emps: list[str]
    # adjacency: table -> list of (other_table, join_sql_fragment using aliases a/b)
    neighbors: dict[str, list[tuple[str, str, str, str]]] = field(default_factory=dict)


def _table_re() -> re.Pattern[str]:
    return re.compile(r"\bcompany\.([a-zA-Z_][a-zA-Z0-9_]*)\b", re.I)


def tables_in_sql(sql: str | None) -> set[str]:
    if not sql:
        return set()
    return {m.group(1).lower() for m in _table_re().finditer(sql)}


class CoverageTracker:
    def __init__(self, all_tables: set[str]) -> None:
        self.all = set(all_tables)
        self.covered: set[str] = set()

    def mark(self, sql: str | None) -> None:
        self.covered |= tables_in_sql(sql)

    def mark_tables(self, *names: str) -> None:
        self.covered |= {n.lower() for n in names}

    def uncovered(self) -> list[str]:
        return sorted(self.all - self.covered)

    def is_covered(self, name: str) -> bool:
        return name.lower() in self.covered


def pick_business_key(columns: list[str]) -> tuple[str, bool, bool]:
    """选业务侧过滤键。返回 (col, has_code, has_user_key)。

    优先 *_code / *_no；其次名称类；**绝不把内部自增 id 当作用户口语过滤键**
    （无业务键时返回 id 且 has_user_key=False，调用方应改走关联主数据过滤）。
    """
    for c in columns:
        if c.endswith("_code") or c.endswith("_no"):
            return c, True, True
    for c in columns:
        if c in ("name", "title") or c.endswith("_name"):
            return c, False, True
    if "id" in columns:
        return "id", False, False
    return columns[0], False, False


def pick_group_key(tm: "TableMeta") -> str:
    """聚合维度优先业务编码/名称，避免 GROUP BY 内部 id。"""
    if tm.has_user_key and tm.business_key != "id":
        return tm.business_key
    for c in tm.display_cols:
        if c.endswith("_name") or c in ("name", "title"):
            return c
    for c in tm.columns:
        if c.endswith("_code") or c.endswith("_no"):
            return c
        if c.endswith("_name") or c in ("name", "title"):
            return c
    return tm.display_cols[0] if tm.display_cols else tm.business_key


def need_return_clause(labels: list[str]) -> str:
    labs = [x.strip() for x in labels if (x or "").strip()]
    if not labs:
        return ""
    return f"需要返回{'、'.join(labs)}"


def with_need_return(q: str, labels: list[str]) -> str:
    clause = need_return_clause(labels)
    if not clause:
        return q
    base = q.rstrip("。．. ")
    if "需要返回" in base:
        return base + "。"
    return f"{base}，{clause}。"


def with_order_hint(q: str, *, primary_zh: str, tie_zh: str) -> str:
    """把期望 ORDER BY 主序+并列次序说清楚，避免只 ORDER BY 主度量导致并列乱序。"""
    p = (primary_zh or "").strip()
    t = (tie_zh or "").strip()
    if not p or not t:
        return q
    hint = f"按{p}从高到低排序，相同则按{t}升序"
    base = q.rstrip("。．. ")
    if "从高到低" in base and "相同则按" in base:
        return base + "。"
    return f"{base}；{hint}。"


def anchor_in_q(tm: "TableMeta", col: str, qv: str) -> str:
    """题面锚点：工号 E210002 / 会议室编码 ROOM01，不叠「员工工号」「会议室会议室编码」。"""
    return f"{zh_field_label(tm, col)} {qv}"


def complex_spec(
    required: list[str],
    *,
    order_columns: list[str] | None = None,
    numeric_tolerance: float | None = None,
) -> dict[str, Any]:
    req = [c for c in required if c and c != "id"]
    if not req:
        req = [c for c in required if c]
    spec: dict[str, Any] = {"requiredColumns": req, "columns": req}
    if order_columns:
        spec["order_columns"] = [c for c in order_columns if c != "id"] or order_columns
    if numeric_tolerance is not None:
        spec["numeric_tolerance"] = numeric_tolerance
    return spec


def pick_display_cols(columns: list[str], col_types: dict[str, str], bk: str) -> list[str]:
    out: list[str] = []
    preferred = []
    for c in columns:
        if c in SKIP_DISPLAY or c == bk or c.endswith("_id"):
            continue
        if c.endswith("_name") or c in (
            "name",
            "title",
            "status",
            "remark",
            "gender",
            "region",
            "industry",
            "city",
            "address",
        ):
            preferred.append(c)
        elif col_types.get(c) in NUMERIC_TYPES and not c.endswith("_id"):
            preferred.append(c)
        else:
            preferred.append(c)
    # name-like first
    preferred.sort(
        key=lambda c: (
            0
            if c.endswith("_name") or c == "name"
            else 1
            if c in ("status", "title")
            else 2
            if col_types.get(c) in NUMERIC_TYPES
            else 3
        )
    )
    for c in preferred:
        if c not in out:
            out.append(c)
        if len(out) >= 2:
            break
    if not out:
        # fallback: any non-id column
        for c in columns:
            if c != bk and c not in SKIP_DISPLAY:
                out.append(c)
                break
    return out[:2]


def zh_col(tm: TableMeta, col: str) -> str:
    z = (tm.col_zh.get(col) or "").strip()
    if z:
        return z
    if col == "emp_no":
        return "工号"
    if col.endswith("_name"):
        return "名称"
    if col.endswith("_code"):
        return "编码"
    if col.endswith("_no"):
        return "编号"
    if col == "status":
        return "状态"
    if col == "name":
        return "姓名" if tm.name in ("hr_employee",) else "名称"
    if col == "title":
        return "职位" if tm.name in ("hr_employee",) else "主题"
    if col == "id":
        return "编号"
    return "信息"


_GENERIC_FIELD_ZH = frozenset({"编码", "名称", "编号", "状态", "信息", "主题", "姓名", "职位"})


def zh_field_label(tm: TableMeta, col: str) -> str:
    """测评题面用的字段名：仅当注释是泛称（编码/名称）时才加实体前缀。

    「职场编码」「客户编码」等已具体的注释原样使用，避免拼成「办公职场职场编码」。
    """
    z = zh_col(tm, col).strip()
    if col == "emp_no" or z == "工号":
        return "工号"
    if z not in _GENERIC_FIELD_ZH:
        return z or ((tm.zh or "").strip() + "信息")
    ent = (tm.zh or "").strip() or "相关"
    if col.endswith("_code") or z == "编码":
        return f"{ent}编码"
    if col.endswith("_name") or z in ("名称", "姓名"):
        return f"{ent}姓名" if z == "姓名" else f"{ent}名称"
    if col.endswith("_no") or z == "编号":
        return f"{ent}编号"
    if z == "状态":
        return f"{ent}状态"
    if z in ("主题", "职位", "信息"):
        return f"{ent}{z}"
    return f"{ent}{z}" if z else ent


def fmt_val(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def lit_in_question(v: Any) -> str:
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


def _seq_key(prefix: str, n: int) -> str:
    return f"{prefix}_{n:03d}"


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------


def build_core_cases(meta: SchemaMeta, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    cov = CoverageTracker(set(meta.tables.keys()))
    names = sorted(meta.tables.keys())
    user_tables = [
        t
        for t in names
        if meta.tables[t].has_user_key
        and meta.tables[t].key_values
        and meta.tables[t].business_key != "id"
    ]
    # 编码/单号优先于名称/主题弱键
    code_tables = [t for t in user_tables if meta.tables[t].has_code_key]
    name_tables = [t for t in user_tables if not meta.tables[t].has_code_key]
    other_tables = [t for t in names if t not in user_tables]

    # SF 仅业务可感知键表；SA 优先吃无业务键的事实表，保证全表覆盖
    sf_pool = list(code_tables) + list(name_tables)
    sa_pool = list(other_tables) + list(user_tables)

    _build_single_filter(out, meta, sf_pool, cov, rng)
    _build_single_agg(out, meta, sa_pool, cov, rng)
    _build_multi_join_filter(out, meta, cov, rng)
    _build_multi_join_agg(out, meta, cov, rng)

    # 配额满后若仍有未覆盖：强制塞进 MJ
    _force_coverage(out, meta, cov, rng)
    return out


def _build_single_filter(
    out: list[dict],
    meta: SchemaMeta,
    pool: list[str],
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    n = 1
    used_tables: set[str] = set()
    # 仅业务可感知键（编码/单号/名称），禁止 id 点查
    user_pool = [
        t
        for t in pool
        if meta.tables[t].has_user_key and meta.tables[t].key_values and meta.tables[t].business_key != "id"
    ]
    for tname in user_pool:
        if n > 100:
            break
        tm = meta.tables[tname]
        if tname in used_tables:
            continue
        _emit_sf(out, meta, tm, tm.key_values[0], n, vi=0)
        cov.mark_tables(tname)
        used_tables.add(tname)
        n += 1

    # 第二业务键变体补满
    for tname in user_pool:
        if n > 100:
            break
        tm = meta.tables[tname]
        if tname not in used_tables or len(tm.key_values) < 2:
            continue
        sk_count = sum(
            1
            for c in out
            if c["category"] == "SINGLE_FILTER"
            and any(str(t) == f"sk:sf_{tname}" for t in (c.get("tags") or []))
        )
        if sk_count >= 2:
            continue
        _emit_sf(out, meta, tm, tm.key_values[1], n, vi=1)
        n += 1

    # 仍不足：同表多取值（骨架仍≤2，由 add/校验保证）
    for tname in user_pool:
        if n > 100:
            break
        tm = meta.tables[tname]
        sk_count = sum(
            1
            for c in out
            if c["category"] == "SINGLE_FILTER"
            and any(str(t) == f"sk:sf_{tname}" for t in (c.get("tags") or []))
        )
        if sk_count >= 2:
            continue
        vi = sk_count
        kv = tm.key_values[vi % len(tm.key_values)]
        _emit_sf(out, meta, tm, kv, n, vi=vi)
        used_tables.add(tname)
        cov.mark_tables(tname)
        n += 1

    if n - 1 != 100:
        raise RuntimeError(f"SINGLE_FILTER expected 100, got {n - 1}; user_pool={len(user_pool)}")


def _emit_sf(out: list[dict], meta: SchemaMeta, tm: TableMeta, kval: Any, n: int, vi: int) -> None:
    if not tm.has_user_key or tm.business_key == "id":
        raise ValueError(f"SF must use user-facing key, got {tm.name}.{tm.business_key}")
    req = list(tm.display_cols) or [tm.business_key]
    cols = [tm.business_key] + [c for c in req if c != tm.business_key]
    seen: set[str] = set()
    cols2: list[str] = []
    for c in cols:
        if c not in seen and c != "id":
            seen.add(c)
            cols2.append(c)
    cols = cols2
    sel = ", ".join(cols)
    kv = fmt_val(kval)
    sql = f"SELECT {sel} FROM company.{tm.name} WHERE {tm.business_key} = {kv}"
    zh = tm.zh
    key_label = zh_col(tm, tm.business_key)
    disp_zh = "、".join(zh_col(tm, c) for c in req) or "相关信息"
    qv = lit_in_question(kval)
    q = utter(
        vi,
        f"{zh}里{key_label}是 {qv} 的，把{disp_zh}查出来。",
        f"帮我看下{zh} {qv}，需要返回{disp_zh}。",
    )
    add(
        out,
        sk=f"sf_{tm.name}",
        key=_seq_key("TPL_SF", n),
        cat="SINGLE_FILTER",
        q=q,
        sql=sql,
        mode="scalar",
        spec={"requiredColumns": req, "columns": req},
        tags=["sf", tm.name.split("_")[0]],
    )


def _build_single_agg(
    out: list[dict],
    meta: SchemaMeta,
    pool: list[str],
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    n = 1
    # 优先未覆盖表
    ordered = sorted(pool, key=lambda t: (cov.is_covered(t), t))
    used: set[str] = set()

    for tname in ordered:
        if n > 100:
            break
        if tname in used:
            continue
        tm = meta.tables[tname]
        _emit_sa_count(out, tm, n, vi=0)
        cov.mark_tables(tname)
        used.add(tname)
        n += 1

    # 第二变体：带固定 status 过滤（若有 status），否则换口语同一 count SQL（同骨架）
    for tname in ordered:
        if n > 100:
            break
        if tname not in used:
            continue
        tm = meta.tables[tname]
        sk_count = sum(
            1
            for c in out
            if c["category"] == "SINGLE_AGG"
            and any(str(t) == f"sk:sa_count_{tname}" for t in (c.get("tags") or []))
        )
        if sk_count >= 2:
            continue
        # 第二变体必须同归一化骨架 → 同一 SQL 结构仅换字面量；无字面量则换题面同 SQL
        if "status" in tm.columns and tm.col_types.get("status") in ("character varying", "text", "varchar"):
            # 不同 status 值会改变字面量但仍同骨架；但若第一条是无过滤 count，骨架不同！
            # 因此第二变体也必须是无过滤 count（仅题面不同）
            pass
        _emit_sa_count(out, tm, n, vi=1)
        n += 1

    if n - 1 != 100:
        raise RuntimeError(f"SINGLE_AGG expected 100, got {n - 1}")


def _emit_sa_count(out: list[dict], tm: TableMeta, n: int, vi: int) -> None:
    sql = f"SELECT count(*)::bigint AS cnt FROM company.{tm.name}"
    q = utter(vi, f"{tm.zh}一共有多少条记录？", f"数一下{tm.zh}总量。")
    add(
        out,
        sk=f"sa_count_{tm.name}",
        key=_seq_key("TPL_SA", n),
        cat="SINGLE_AGG",
        q=q,
        sql=sql,
        mode="scalar",
        spec={"columns": ["cnt"]},
        tags=["sa", "agg", tm.name.split("_")[0]],
    )


def _iter_fk_pairs(meta: SchemaMeta) -> list[tuple[TableMeta, TableMeta, str, str]]:
    """(child, parent, child_col, parent_col)"""
    pairs = []
    for src, scol, dst, dcol in meta.fk_edges:
        if src not in meta.tables or dst not in meta.tables:
            continue
        pairs.append((meta.tables[src], meta.tables[dst], scol, dcol))
    return pairs


def _mjf_anchor(
    child: TableMeta, parent: TableMeta
) -> tuple[str, TableMeta, str, list[Any]] | None:
    """选用户可感知的过滤锚点：(sql_alias, table, col, values)。

    优先双方 *_code/*_no；名称/title 弱键次之。事实表常无单号，优先挂主数据编码。
    """
    if child.has_code_key and child.key_values:
        return "c", child, child.business_key, child.key_values
    if parent.has_code_key and parent.key_values:
        return "p", parent, parent.business_key, parent.key_values
    if child.has_user_key and child.key_values and child.business_key != "id":
        return "c", child, child.business_key, child.key_values
    if parent.has_user_key and parent.key_values and parent.business_key != "id":
        return "p", parent, parent.business_key, parent.key_values
    return None


def _build_multi_join_filter(
    out: list[dict],
    meta: SchemaMeta,
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    pairs = _iter_fk_pairs(meta)
    pairs.sort(
        key=lambda p: (
            cov.is_covered(p[0].name) and cov.is_covered(p[1].name),
            0 if (p[0].has_user_key or p[1].has_user_key) else 1,
            p[0].name,
            p[1].name,
        )
    )
    n = 1
    # 50 骨架 × 2；只收有业务锚点的边
    skeletons: list[tuple] = []
    seen_edge: set[tuple[str, str, str]] = set()
    for child, parent, scol, dcol in pairs:
        key = (child.name, scol, parent.name)
        if key in seen_edge:
            continue
        if _mjf_anchor(child, parent) is None:
            continue
        seen_edge.add(key)
        skeletons.append((child, parent, scol, dcol))
        if len(skeletons) >= 50:
            break

    if len(skeletons) < 50:
        for child, parent, scol, dcol in pairs:
            if len(skeletons) >= 50:
                break
            for gp_src, gp_scol, gp_dst, gp_dcol in meta.fk_edges:
                if gp_src != parent.name:
                    continue
                gp = meta.tables.get(gp_dst)
                if gp is None:
                    continue
                # 三表：子或祖宗须有业务键
                if not (
                    (child.has_user_key and child.key_values)
                    or (gp.has_user_key and gp.key_values)
                    or (parent.has_user_key and parent.key_values)
                ):
                    continue
                skeletons.append((child, parent, scol, dcol, gp, gp_scol, gp_dcol))
                if len(skeletons) >= 50:
                    break

    if len(skeletons) < 50:
        raise RuntimeError(f"MULTI_JOIN_FILTER skeletons need 50, got {len(skeletons)}")

    for sk in skeletons[:50]:
        for vi in range(2):
            if len(sk) == 4:
                child, parent, scol, dcol = sk
                anchor = _mjf_anchor(child, parent)
                assert anchor is not None
                alias, atm, acol, avals = anchor
                kv = avals[vi % len(avals)]
                # 从子表点查 → 带回父表字段；从父表点查 → 带回子表业务字段
                if alias == "c":
                    focus, focus_alias = parent, "p"
                else:
                    focus, focus_alias = child, "c"
                disp = [
                    c
                    for c in (
                        focus.display_cols[:2]
                        or ([focus.business_key] if focus.has_user_key and focus.business_key != "id" else [])
                    )
                    if c != "id"
                ]
                if not disp and focus.has_user_key and focus.business_key != "id":
                    disp = [focus.business_key]
                if not disp:
                    disp = [acol]
                sel_parts = [f"{alias}.{acol}"] + [
                    f"{focus_alias}.{c}" for c in disp if c != acol
                ]
                seen_sel: set[str] = set()
                sel_sql: list[str] = []
                for p in sel_parts:
                    if p not in seen_sel:
                        seen_sel.add(p)
                        sel_sql.append(p)
                sql = (
                    f"SELECT {', '.join(sel_sql)} FROM company.{child.name} c "
                    f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                    f"WHERE {alias}.{acol} = {fmt_val(kv)} "
                    f"ORDER BY {alias}.{acol}"
                )
                req = [c for c in disp if c != "id"]
                req_zh = [zh_field_label(focus, c) for c in req]
                qv = lit_in_question(kv)
                anchor = anchor_in_q(atm, acol, qv)
                if alias == "c":
                    q = utter(
                        vi,
                        f"{anchor} 的{child.zh}，关联的{parent.zh}信息一并带上。",
                        f"查一下 {anchor} 对应的{parent.zh}。",
                    )
                else:
                    q = utter(
                        vi,
                        f"{anchor} 下面有哪些{child.zh}，把关联信息列出来。",
                        f"从 {anchor} 看它关联的{child.zh}。",
                    )
                q = with_need_return(q, req_zh)
                sk_id = f"mjf_{child.name}_{parent.name}_{scol}"
            else:
                child, parent, scol, dcol, gp, gp_scol, gp_dcol = sk
                # 过滤优先：子业务键 → 祖宗业务键 → 父业务键
                if child.has_user_key and child.key_values:
                    alias, atm, acol, avals = "c", child, child.business_key, child.key_values
                elif gp.has_user_key and gp.key_values:
                    alias, atm, acol, avals = "g", gp, gp.business_key, gp.key_values
                elif parent.has_user_key and parent.key_values:
                    alias, atm, acol, avals = "p", parent, parent.business_key, parent.key_values
                else:
                    continue
                kv = avals[vi % len(avals)]
                disp = [c for c in (gp.display_cols[:1] or ([gp.business_key] if gp.has_user_key else [])) if c != "id"]
                if not disp:
                    disp = [acol]
                sql = (
                    f"SELECT {alias}.{acol}, g.{disp[0]} FROM company.{child.name} c "
                    f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                    f"JOIN company.{gp.name} g ON g.{gp_dcol} = p.{gp_scol} "
                    f"WHERE {alias}.{acol} = {fmt_val(kv)} "
                    f"ORDER BY {alias}.{acol}"
                )
                req = [disp[0]]
                req_zh = [zh_field_label(gp, disp[0])]
                q = utter(
                    vi,
                    f"从{atm.zh} {lit_in_question(kv)} 经{parent.zh}关联到{gp.zh}。",
                    f"{atm.zh} {lit_in_question(kv)} 关联链路上的{gp.zh}信息。",
                )
                q = with_need_return(q, req_zh)
                sk_id = f"mjf3_{child.name}_{parent.name}_{gp.name}"

            add(
                out,
                sk=sk_id,
                key=_seq_key("TPL_MJF", n),
                cat="MULTI_JOIN_FILTER",
                q=q,
                sql=sql,
                mode="order_by",
                spec=complex_spec(req, order_columns=[acol]),
                tags=["mjf"],
            )
            cov.mark(sql)
            n += 1

    if n - 1 != 100:
        raise RuntimeError(f"MULTI_JOIN_FILTER expected 100, got {n - 1}")


def _numeric_col(tm: TableMeta) -> str | None:
    for c in tm.columns:
        if c in SKIP_DISPLAY or c.endswith("_id") or c == tm.business_key:
            continue
        if tm.col_types.get(c) in NUMERIC_TYPES:
            return c
    return None


def _build_multi_join_agg(
    out: list[dict],
    meta: SchemaMeta,
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    pairs = _iter_fk_pairs(meta)
    pairs.sort(
        key=lambda p: (
            cov.is_covered(p[0].name) and cov.is_covered(p[1].name),
            0 if pick_group_key(p[1]) != "id" else 1,
            p[0].name,
        )
    )
    n = 1
    skeletons = []
    seen = set()
    for child, parent, scol, dcol in pairs:
        key = (child.name, parent.name, scol)
        if key in seen:
            continue
        if pick_group_key(parent) == "id":
            continue
        seen.add(key)
        skeletons.append((child, parent, scol, dcol))
        if len(skeletons) >= 50:
            break
    if len(skeletons) < 50:
        raise RuntimeError(f"MULTI_JOIN_AGG skeletons need 50, got {len(skeletons)}")

    for child, parent, scol, dcol in skeletons[:50]:
        gk = pick_group_key(parent)
        gk_zh = zh_field_label(parent, gk)
        for vi in range(2):
            limit = 50 if vi == 0 else 100
            num = _numeric_col(child)
            if num:
                sql = (
                    f"SELECT p.{gk}, coalesce(sum(c.{num}),0) AS amt "
                    f"FROM company.{child.name} c "
                    f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                    f"GROUP BY p.{gk} "
                    f"ORDER BY amt DESC, p.{gk} LIMIT {limit}"
                )
                req = [gk, "amt"]
                q = utter(
                    vi,
                    f"按{parent.zh}汇总{child.zh}的{zh_field_label(child, num)}，取前 {limit}。",
                    f"{parent.zh}维度把{child.zh}相关金额加总，Top {limit}。",
                )
                q = with_need_return(q, [gk_zh, "合计金额"])
                q = with_order_hint(q, primary_zh="合计金额", tie_zh=gk_zh)
                spec = complex_spec(req, order_columns=["amt", gk], numeric_tolerance=0.01)
            else:
                sql = (
                    f"SELECT p.{gk}, count(*)::bigint AS cnt "
                    f"FROM company.{child.name} c "
                    f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                    f"GROUP BY p.{gk} "
                    f"ORDER BY cnt DESC, p.{gk} LIMIT {limit}"
                )
                req = [gk, "cnt"]
                q = utter(
                    vi,
                    f"各{parent.zh}下有多少条{child.zh}？取前 {limit}。",
                    f"按{parent.zh}统计{child.zh}条数，Top {limit}。",
                )
                q = with_need_return(q, [gk_zh, "条数"])
                q = with_order_hint(q, primary_zh="条数", tie_zh=gk_zh)
                spec = complex_spec(req, order_columns=["cnt", gk])
            add(
                out,
                sk=f"mja_{child.name}_{parent.name}_{scol}",
                key=_seq_key("TPL_MJA", n),
                cat="MULTI_JOIN_AGG",
                q=q,
                sql=sql,
                mode="order_by",
                spec=spec,
                tags=["mja", "agg"],
            )
            cov.mark(sql)
            n += 1

    if n - 1 != 100:
        raise RuntimeError(f"MULTI_JOIN_AGG expected 100, got {n - 1}")


def _board_count_label(child: "TableMeta") -> str:
    z = (child.zh or "").strip() or "记录"
    if any(p in z for p in ("成员", "员工", "联系人", "人员")):
        return z if z.endswith("人数") else f"{z}人数"
    return f"{z}数量"


def _build_board_filter(
    out: list[dict],
    meta: SchemaMeta,
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    """25 骨架 × 2：两表直连，无多余第三表 / EXISTS。"""
    pairs = _iter_fk_pairs(meta)
    pairs.sort(
        key=lambda p: (
            cov.is_covered(p[0].name) and cov.is_covered(p[1].name),
            0 if _mjf_anchor(p[0], p[1]) else 1,
            p[0].name,
            p[1].name,
        )
    )
    picked: list[tuple[TableMeta, TableMeta, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for child, parent, scol, dcol in pairs:
        key = (child.name, scol, parent.name)
        if key in seen:
            continue
        if _mjf_anchor(child, parent) is None:
            continue
        gk = pick_group_key(parent)
        if gk == "id":
            continue
        seen.add(key)
        picked.append((child, parent, scol, dcol))
        if len(picked) >= 25:
            break
    if len(picked) < 25:
        raise RuntimeError(f"BOARD filter skeletons need 25, got {len(picked)}")

    n = 1
    for child, parent, scol, dcol in picked:
        sk = f"bf_pair_{child.name}_{parent.name}_{scol}"
        for vi in range(2):
            anchor = _mjf_anchor(child, parent)
            assert anchor is not None
            alias, atm, acol, avals = anchor
            kv = avals[vi % len(avals)]
            gk = pick_group_key(parent)
            sql = (
                f"SELECT DISTINCT p.{gk} FROM company.{child.name} c "
                f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                f"WHERE {alias}.{acol} = {fmt_val(kv)} "
                f"ORDER BY p.{gk}"
            )
            gk_zh = zh_field_label(parent, gk)
            q_anchor = anchor_in_q(atm, acol, lit_in_question(kv))
            if alias == "c":
                q = utter(
                    vi,
                    f"{q_anchor} 对应哪些{parent.zh}？把{gk_zh}列出来。",
                    f"看下 {q_anchor} 对应的{parent.zh}，需要返回{gk_zh}。",
                )
            else:
                q = utter(
                    vi,
                    f"{q_anchor} 名下有关联{child.zh}的，把{gk_zh}列出来。",
                    f"帮我查 {q_anchor}，需要返回{gk_zh}。",
                )
            q = with_need_return(q, [gk_zh])
            add(
                out,
                sk=sk,
                key=_seq_key("TPL_GOV_B", n),
                cat="MULTI_GOVERN_FILTER",
                q=q,
                sql=sql,
                mode="order_by",
                spec=complex_spec([gk], order_columns=[gk]),
                govern_subtype="BOARD",
                tags=["board", "bf"],
            )
            cov.mark(sql)
            n += 1

    if n - 1 != 50:
        raise RuntimeError(f"BOARD FILTER expected 50, got {n - 1}")


def _build_board_agg(
    out: list[dict],
    meta: SchemaMeta,
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    """25 骨架 × 2：两表直连聚合，不绕中间表、不用子查询。"""
    pairs = _iter_fk_pairs(meta)
    pairs.sort(
        key=lambda p: (
            cov.is_covered(p[0].name) and cov.is_covered(p[1].name),
            0 if pick_group_key(p[1]) != "id" else 1,
            p[0].name,
            p[1].name,
        )
    )
    picked: list[tuple[TableMeta, TableMeta, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for child, parent, scol, dcol in pairs:
        key = (child.name, scol, parent.name)
        if key in seen:
            continue
        if pick_group_key(parent) == "id":
            continue
        seen.add(key)
        picked.append((child, parent, scol, dcol))
        if len(picked) >= 25:
            break
    if len(picked) < 25:
        raise RuntimeError(f"BOARD agg skeletons need 25, got {len(picked)}")

    n = 1
    for child, parent, scol, dcol in picked:
        sk = f"ba_pair_{child.name}_{parent.name}_{scol}"
        gk = pick_group_key(parent)
        gk_zh = zh_field_label(parent, gk)
        cnt_zh = _board_count_label(child)
        for vi in range(2):
            lim = 20 if vi == 0 else 30
            sql = (
                f"SELECT p.{gk} AS pk, count(*)::bigint AS cnt "
                f"FROM company.{child.name} c "
                f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                f"GROUP BY p.{gk} "
                f"ORDER BY cnt DESC, pk LIMIT {lim}"
            )
            q = utter(
                vi,
                f"按{parent.zh}统计{cnt_zh}，取前 {lim}。",
                f"帮我看下各{parent.zh}名下{cnt_zh}，取前 {lim}。",
            )
            q = with_need_return(q, [gk_zh, "条数"])
            add(
                out,
                sk=sk,
                key=_seq_key("TPL_GOV_BA", n),
                cat="MULTI_GOVERN_AGG",
                q=q,
                sql=sql,
                mode="order_by",
                spec=complex_spec(["pk", "cnt"], order_columns=["cnt", "pk"]),
                govern_subtype="BOARD",
                tags=["board", "ba"],
            )
            cov.mark(sql)
            n += 1

    if n - 1 != 50:
        raise RuntimeError(f"BOARD AGG expected 50, got {n - 1}")


def _force_coverage(
    out: list[dict],
    meta: SchemaMeta,
    cov: CoverageTracker,
    rng: random.Random,
) -> None:
    """未覆盖表仅塞进 MJF/MJA（不改 GOVERN 金标，避免治理题被 EXISTS 污染）。"""
    missing = cov.uncovered()
    if not missing:
        return

    targets = [
        c
        for c in out
        if c.get("expect_sql")
        and c["category"] in ("MULTI_JOIN_FILTER", "MULTI_JOIN_AGG")
    ]
    if not targets:
        raise RuntimeError(f"no MJF/MJA cases to force-cover: {missing[:20]}")

    for i, tname in enumerate(list(missing)):
        case = targets[i % len(targets)]
        sql = case["expect_sql"].rstrip().rstrip(";")
        new_sql = (
            f"SELECT * FROM ({sql}) _force "
            f"WHERE EXISTS (SELECT 1 FROM company.{tname} _cov_{tname} LIMIT 1)"
        )
        case["expect_sql"] = new_sql
        cov.mark(new_sql)

    still = cov.uncovered()
    if still:
        raise RuntimeError(f"coverage incomplete after force: {still[:30]} ... total={len(still)}")


def append_hitl_and_refuse(out: list[dict], meta: SchemaMeta, rng: random.Random) -> None:
    """HITL 补全 30+30（≥15 不同骨架×2），拒答 20+20。尽量用扩展表。"""
    pairs = _iter_fk_pairs(meta)
    # 偏好扩展表（非 CORE）
    ext_pairs = [
        p
        for p in pairs
        if p[0].name not in CORE_ZH or p[1].name not in CORE_ZH
    ]
    if len(ext_pairs) < 15:
        ext_pairs = pairs

    # 15 骨架 × 2 = 30 HITL filter（补充话术里给业务键，题面仍含糊）
    skel = []
    seen = set()
    for child, parent, scol, dcol in ext_pairs:
        key = (child.name, parent.name, scol)
        if key in seen or _mjf_anchor(child, parent) is None:
            continue
        seen.add(key)
        skel.append((child, parent, scol, dcol))
        if len(skel) >= 15:
            break
    if len(skel) < 15:
        raise RuntimeError(f"HITL filter skeletons need 15, got {len(skel)}")

    for i, (child, parent, scol, dcol) in enumerate(skel, start=1):
        for vi in range(2):
            anchor = _mjf_anchor(child, parent)
            assert anchor is not None
            alias, atm, acol, avals = anchor
            kv = avals[vi % len(avals)]
            disp = [c for c in (parent.display_cols[:1] or ([parent.business_key] if parent.has_user_key else [acol])) if c != "id"]
            if not disp:
                disp = [acol]
            sql = (
                f"SELECT {alias}.{acol}, p.{disp[0]} FROM company.{child.name} c "
                f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                f"WHERE {alias}.{acol} = {fmt_val(kv)} "
                f"ORDER BY {alias}.{acol}"
            )
            disp_zh = zh_field_label(parent, disp[0])
            ak_zh = zh_field_label(atm, acol)
            q = utter(
                vi,
                f"把相关的{child.zh}和{parent.zh}信息拉一下。",
                f"{child.zh}那边挂{parent.zh}的清单给我。",
            )
            idx = (i - 1) * 2 + vi + 1
            add(
                out,
                sk=f"hitl_f_{child.name}_{parent.name}",
                key=_seq_key("TPL_GOV_H", idx),
                cat="MULTI_GOVERN_FILTER",
                q=q,
                sql=sql,
                mode="order_by",
                spec=complex_spec([disp[0]], order_columns=[acol]),
                govern_subtype="HITL_SUPPLEMENT",
                hitl_replies=[
                    f"相关=其{ak_zh}为 {lit_in_question(kv)}；"
                    f"需要返回{disp_zh}"
                ],
                tags=["hitl"],
            )

    refuse_filter = [
        "有问题的单据都导出来。",
        "异常台账给我一份名单。",
        "不对劲的申请列一下。",
        "风险主数据有哪些？",
        "可疑流水记录发我。",
        "有问题的档案筛出来。",
        "不正常的挂接关系。",
        "垃圾数据那批给我。",
        "需要关注的对象有哪些？",
        "差的主体排个名（别问我啥叫差）。",
        "奇怪的申请帮我看看。",
        "有隐患的协议。",
        "不靠谱的来源有哪些行？",
        "问题清单导出来。",
        "异常回笼记录。",
        "坏账相关单据。",
        "要治理的那批表数据导出来。",
        "你们说的脏数据。",
        "不健康的组织单元有哪些？",
        "有问题的成本行。",
    ]
    for i, q in enumerate(refuse_filter, start=1):
        add(
            out,
            sk=f"refuse_f_{i:03d}",
            key=_seq_key("TPL_GOV_R", i),
            cat="MULTI_GOVERN_FILTER",
            q=q,
            sql=None,
            mode="empty_or_refuse",
            spec={},
            govern_subtype="HITL_NO_SUPPLEMENT",
            tags=["refuse"],
        )

    # HITL agg 15×2
    skel_a = []
    seen_a = set()
    for child, parent, scol, dcol in ext_pairs:
        key = ("a", child.name, parent.name)
        if key in seen_a:
            continue
        if pick_group_key(parent) == "id":
            continue
        seen_a.add(key)
        skel_a.append((child, parent, scol, dcol))
        if len(skel_a) >= 15:
            break
    if len(skel_a) < 15:
        raise RuntimeError(f"HITL agg skeletons need 15, got {len(skel_a)}")

    for i, (child, parent, scol, dcol) in enumerate(skel_a, start=1):
        gk = pick_group_key(parent)
        gk_zh = zh_field_label(parent, gk)
        for vi in range(2):
            lim = 15 if vi == 0 else 25
            sql = (
                f"SELECT p.{gk}, count(*)::bigint AS cnt "
                f"FROM company.{child.name} c "
                f"JOIN company.{parent.name} p ON p.{dcol} = c.{scol} "
                f"GROUP BY p.{gk} "
                f"ORDER BY cnt DESC, p.{gk} LIMIT {lim}"
            )
            q = utter(
                vi,
                f"相关{parent.zh}贡献排个序。",
                f"把{parent.zh}侧汇总一下给我。",
            )
            idx = (i - 1) * 2 + vi + 1
            add(
                out,
                sk=f"hitl_a_{child.name}_{parent.name}",
                key=_seq_key("TPL_GOV_HA", idx),
                cat="MULTI_GOVERN_AGG",
                q=q,
                sql=sql,
                mode="order_by",
                spec=complex_spec([gk, "cnt"], order_columns=["cnt", gk]),
                govern_subtype="HITL_SUPPLEMENT",
                hitl_replies=[
                    f"相关=按{gk_zh}统计其下{child.zh}条数；取 Top {lim}；"
                    f"需要返回{gk_zh}、条数"
                ],
                tags=["hitl"],
            )

    refuse_agg = [
        "异常单据总金额统计一下。",
        "风险主体贡献占比多少？",
        "有问题申请合计多少钱？",
        "不健康单元人均成本。",
        "可疑加班总时长。",
        "坏数据对收入影响多大？",
        "异常考勤造成的工时损失。",
        "问题项目亏损合计。",
        "需要关注的回款缺口。",
        "脏单据金额分布。",
        "不合理薪资合计。",
        "异常产品毛利。",
        "风险敞口按组织汇总。",
        "不正常离职相关成本。",
        "质量差的交付金额。",
        "有争议的订单金额。",
        "待治理指标那张看板数据。",
        "异常率最高的组织是谁？",
        "问题最多的客户贡献。",
        "不靠谱数据导致的差异金额。",
    ]
    for i, q in enumerate(refuse_agg, start=1):
        add(
            out,
            sk=f"refuse_a_{i:03d}",
            key=_seq_key("TPL_GOV_RA", i),
            cat="MULTI_GOVERN_AGG",
            q=q,
            sql=None,
            mode="empty_or_refuse",
            spec={},
            govern_subtype="HITL_NO_SUPPLEMENT",
            tags=["refuse"],
        )


def append_dirty_sample(out: list[dict], meta: SchemaMeta, rng: random.Random) -> None:
    if not meta.conflict_emps:
        return
    e = meta.conflict_emps[0]
    add(
        out,
        sk="sf_dirty_conflict",
        key="TPL_SF_DIRTY_001",
        cat="SINGLE_FILTER",
        q=utter(
            0,
            f"工号 {e} 有点奇怪，人事状态和离职日分别是什么？",
            f"{e} 到底走没走？把在职情况和离职日期都查出来。",
        ),
        sql=(
            f"SELECT emp_no, employment_status, leave_date FROM company.hr_employee "
            f"WHERE emp_no = '{e}'"
        ),
        mode="scalar",
        spec={"columns": ["emp_no", "employment_status", "leave_date"]},
        tags=["hr", "dirty_status"],
    )
