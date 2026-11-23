from dbc_askdata.graph.sql_tables import (
    described_key_from_args,
    extract_tables_from_sql,
    normalize_table_key,
    source_tables_from_draft,
)


def test_normalize_table_key():
    assert normalize_table_key("company.hr_employee") == "company.hr_employee"
    assert normalize_table_key("hr_employee", default_schema="company") == "company.hr_employee"
    assert normalize_table_key("HR_Employee", default_schema="Company") == "company.hr_employee"


def test_extract_tables_from_sql_skips_none():
    tables = extract_tables_from_sql(
        "SELECT e.emp_no FROM company.hr_employee e "
        "JOIN company.org_department d ON d.id = e.dept_id"
    )
    assert ("company", "hr_employee") in tables or ("company", "hr_employee".lower()) in {
        (s, n.lower()) for s, n in tables
    }
    names = {(s.lower() if s else None, n.lower()) for s, n in tables}
    assert ("company", "hr_employee") in names
    assert ("company", "org_department") in names


def test_source_tables_from_draft_excludes_node_refs():
    draft = {
        "name": "t",
        "nodes": [
            {
                "id": "n1",
                "type": "GOVERN",
                "sql": "SELECT id FROM company.prj_project WHERE status = 'active'",
            },
            {
                "id": "n2",
                "type": "QUERY",
                "sql": "SELECT * FROM __node_n1__ WHERE id > 0",
            },
        ],
    }
    keys = source_tables_from_draft(draft, default_schema="company")
    assert "company.prj_project" in keys
    assert not any("node" in k for k in keys)


def test_described_key_from_args():
    assert (
        described_key_from_args({"table": "hr_employee", "schema": "company"})
        == "company.hr_employee"
    )
    assert described_key_from_args({"table": "company.hr_employee"}) == "company.hr_employee"
