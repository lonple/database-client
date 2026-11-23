"""按文案+SQL 规则重写模板用例的 requiredColumns（原地改 JSONL）。"""
from __future__ import annotations

import json
import re
from pathlib import Path

import sqlglot
from sqlglot import exp

CASES_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo-company" / "eval" / "cases"


def _outer_select(sql: str) -> exp.Select | None:
    text = (sql or "").strip()
    if not text:
        return None
    try:
        tree = sqlglot.parse_one(text, read="postgres")
    except Exception:
        return None
    if isinstance(tree, exp.Select):
        return tree
    if isinstance(tree, exp.With) and isinstance(tree.this, exp.Select):
        return tree.this
    return None


def _unwrap_cast(node: exp.Expression | None) -> exp.Expression | None:
    cur = node
    while isinstance(cur, exp.Cast):
        cur = cur.this
    return cur


def _first_col(node: exp.Expression | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, exp.Column):
        return (node.name or "").strip().lower() or None
    for ch in node.iter_expressions():
        found = _first_col(ch)
        if found:
            return found
    return None


def _dedupe(cols: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for c in cols:
        n = (c or "").strip().lower()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _is_count(node: exp.Expression | None) -> bool:
    return isinstance(_unwrap_cast(node), exp.Count)


def _is_sum_like(node: exp.Expression | None) -> bool:
    inner = _unwrap_cast(node)
    if isinstance(inner, (exp.Sum, exp.Avg, exp.Min, exp.Max)):
        return True
    if isinstance(inner, exp.Coalesce):
        parts = [inner.this, *(inner.expressions or [])]
        return any(_is_sum_like(p) or _is_count(p) for p in parts if p is not None)
    return False


def analyze_sql(sql: str) -> tuple[list[str], list[str], list[str], bool]:
    """返回 (all_proj_sources, group_cols, metric_cols, has_agg)。"""
    sel = _outer_select(sql)
    if sel is None:
        return [], [], [], False

    gcols: list[str] = []
    g = sel.args.get("group")
    if g:
        for e in g.expressions or []:
            if isinstance(e, exp.Column):
                gcols.append(e.name.lower())
            elif isinstance(e, exp.Alias) and isinstance(e.this, exp.Column):
                gcols.append(e.this.name.lower())
    gcols = _dedupe(gcols)

    proj: list[str] = []
    metrics: list[str] = []
    has_agg = False
    for e in sel.expressions or []:
        node = e.this if isinstance(e, exp.Alias) else e
        if _is_count(node):
            has_agg = True
            proj.append("cnt")
            metrics.append("cnt")
            continue
        if _is_sum_like(node):
            has_agg = True
            col = _first_col(node)
            if col:
                proj.append(col)
                metrics.append(col)
            else:
                alias = (e.alias or "").lower() if isinstance(e, exp.Alias) else ""
                name = "total_amount" if alias in {"amt", "total", "amount", ""} else alias
                proj.append(name)
                metrics.append(name)
            continue
        if isinstance(node, exp.Column):
            proj.append(node.name.lower())
        elif isinstance(node, exp.Cast) and isinstance(node.this, exp.Column):
            proj.append(node.this.name.lower())
        elif isinstance(e, exp.Alias) and isinstance(e.this, exp.Column):
            proj.append(e.this.name.lower())

    return _dedupe(proj), gcols, _dedupe(metrics), has_agg


def suggest_required(question: str, sql: str, mode: str, old_spec: dict) -> list[str]:
    if (mode or "").lower() == "empty_or_refuse":
        return []

    proj, gcols, metrics, has_agg = analyze_sql(sql)
    q = question or ""

    # —— 分组统计 / 标量聚合 ——
    if gcols or has_agg:
        if gcols:
            return _dedupe([*gcols, *metrics])
        # 纯标量
        if metrics:
            return metrics
        return proj or ["cnt"]

    # —— 明细 / 列表 ——
    sql_set = set(proj)

    # SQL 只有一列：该列即必须
    if len(proj) == 1:
        return proj[:]

    # 哪个部门 → dept_name
    if any(k in q for k in ("哪个部门", "什么部门", "编制在", "挂靠", "属于哪个部门", "中文部门名", "花名册对一下")):
        if "dept_name" in sql_set:
            return ["dept_name"]

    # 姓名 + 入职
    if (("姓名" in q) or ("名字" in q)) and ("入职" in q):
        return [c for c in ("name", "hire_date") if c in sql_set] or ["name", "hire_date"]

    # 邮箱 + 手机
    if (("邮箱" in q) or ("邮件" in q)) and (("手机" in q) or ("电话" in q)):
        return [c for c in ("email", "phone") if c in sql_set] or ["email", "phone"]

    # 人事状态
    if any(k in q for k in ("人事状态", "还在职吗", "在职吗")):
        if "employment_status" in sql_set:
            return ["employment_status"]

    # 常驻城市
    if any(k in q for k in ("常驻", "办公城市", "城市写的是")):
        if "base_city" in sql_set:
            return ["base_city"]

    # 列出工号
    if re.search(r"(列出|列出来).{0,8}工号|工号.{0,8}(列出|列出来)", q):
        if "emp_no" in sql_set:
            return ["emp_no"]

    # 其它文案点名
    pairs = [
        (["客户编码", "客户代码"], "customer_code"),
        (["客户名"], "customer_name"),
        (["产品编码", "产品代码"], "product_code"),
        (["项目编码", "项目编号"], "project_code"),
        (["订单号"], "order_no"),
        (["报销单号"], "claim_no"),
        (["部门编码"], "dept_code"),
    ]
    want: list[str] = []
    for keys, col in pairs:
        if any(k in q for k in keys) and col in sql_set:
            want.append(col)
    if want:
        return _dedupe(want)

    # 兜底：SQL 列去掉 emp_no（标识非必须）
    fallback = [c for c in proj if c != "emp_no"]
    return fallback or proj or _fallback_old(old_spec)


def _fallback_old(spec: dict) -> list[str]:
    raw = (
        spec.get("requiredColumns")
        or spec.get("columns")
        or list(spec.get("key_columns") or []) + list(spec.get("value_columns") or [])
        or []
    )
    out = []
    for x in raw:
        n = str(x).lower()
        if n == "amt":
            n = "total_amount"
        out.append(n)
    return _dedupe(out)


def rewrite_file(path: Path) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    out_lines: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        obj = json.loads(line)
        spec = dict(obj.get("compare_spec") or {})
        mode = obj.get("compare_mode") or ""
        req = suggest_required(obj.get("question") or "", obj.get("expect_sql") or "", mode, spec)
        old = _fallback_old(spec)
        if req != old:
            changed += 1
        new_spec: dict = {}
        if "numeric_tolerance" in spec:
            new_spec["numeric_tolerance"] = spec["numeric_tolerance"]
        if "tolerance" in spec:
            new_spec["tolerance"] = spec["tolerance"]
        new_spec["requiredColumns"] = req
        new_spec["columns"] = req  # 兼容旧读取
        obj["compare_spec"] = new_spec
        out_lines.append(json.dumps(obj, ensure_ascii=False, separators=(",", ": ")))
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return len(out_lines), changed


def main() -> None:
    total = changed = 0
    for path in sorted(CASES_DIR.glob("*.jsonl")):
        if path.name == "smoke.jsonl":
            continue
        n, c = rewrite_file(path)
        total += n
        changed += c
        print(f"{path.name}: cases={n} changed={c}")
    print(f"done total={total} changed={changed}")


if __name__ == "__main__":
    main()
