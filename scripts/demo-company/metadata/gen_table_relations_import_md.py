"""从 company-table-fks.json 生成可导入的表关系 Markdown。

输出：table-relations.import.md
导入约定见文件头；dbc-graph POST /api/graphs/import-md 可解析。
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SEED_JSON = REPO / "dbc-graph" / "src" / "main" / "resources" / "seed" / "company-table-fks.json"
OUT = HERE / "table-relations.import.md"


def main() -> None:
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    tables = data.get("tables") or []
    fks = data.get("fks") or []

    lines: list[str] = [
        "# company 表关系",
        "",
        "> 可导入格式：元数据用列表；外键用表格。导入时每条 FK 生成双向边（父→子=父列名，子→父=子列名）。",
        "",
        "- code: `default`",  # 问数固定按编码 default 解析图谱
        "- name: `company 表关系`",
        "- summary: `demo-company 库表外键图谱（子表.col → 父表.col）`",
        "- productName: `dbc产品`",
        "- bidirectional: `true`",
        "",
        f"> 共 {len(tables)} 张表 / {len(fks)} 条外键（来源 seed/company-table-fks.json）",
        "",
        "## 外键",
        "",
        "| 子表 | 子列 | 父表 | 父列 | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for fk in fks:
        child = fk.get("child", "")
        child_col = fk.get("childCol", "")
        parent = fk.get("parent", "")
        parent_col = fk.get("parentCol", "")
        desc = (fk.get("description") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{child}` | `{child_col}` | `{parent}` | `{parent_col}` | {desc} |")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} tables={len(tables)} fks={len(fks)}")


if __name__ == "__main__":
    main()
