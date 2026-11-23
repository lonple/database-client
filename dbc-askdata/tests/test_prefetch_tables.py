from dbc_askdata.checkpoint.store import infer_resume_from
from dbc_askdata.graph.generate import route_from_draft, select_prefetch_tables


def test_select_prefetch_keeps_physical_names_in_recall_order() -> None:
    catalog = {
        "items": [
            {"name": "员工表"},
            {"name": "company.hr_employee"},
            {"name": "hr_employee"},
            {"name": "org_department"},
            {"name": "fin reimburse"},
            {"name": "crm_customer"},
        ]
    }
    assert select_prefetch_tables(catalog) == ["company.hr_employee", "org_department"]


def test_select_prefetch_puts_confirmed_table_first() -> None:
    catalog = {"items": [{"name": "hr_employee"}, {"name": "org_department"}]}
    picked = select_prefetch_tables(catalog, {"table": "crm_customer"})
    assert picked == ["crm_customer", "hr_employee"]


def test_route_from_draft() -> None:
    assert route_from_draft({"nodes": [{"type": "QUERY", "sql": "select 1"}]}) == "QUERY"
    # 多节点 / GOVERN 亦固定为 QUERY（生成侧已下线拆层）
    assert (
        route_from_draft(
            {
                "nodes": [
                    {"type": "GOVERN", "sql": "select 1"},
                    {"type": "QUERY", "sql": "select 2"},
                ]
            }
        )
        == "QUERY"
    )
    assert (
        route_from_draft(
            {"nodes": [{"type": "QUERY", "sql": "select 1"}, {"type": "QUERY", "sql": "select 2"}]}
        )
        == "QUERY"
    )


def test_resume_skips_removed_fine_router() -> None:
    assert infer_resume_from({"interrupted_node": "fine_router", "catalog": {"items": []}}) == "gather"
    assert (
        infer_resume_from(
            {"interrupted_node": "govern_plan", "pre_described_tables": [{"table": "t"}]}
        )
        == "build"
    )
    assert infer_resume_from({"interrupted_node": "verify", "route": "GOVERN"}) == "build"
