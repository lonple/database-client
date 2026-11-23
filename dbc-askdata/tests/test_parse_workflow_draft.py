"""parse_workflow_draft：多节点/GOVERN 展平为单 QUERY。"""

from dbc_askdata.verify.repair import parse_workflow_draft


def test_single_query_passthrough() -> None:
    raw = '{"name":"t","nodes":[{"id":"n1","type":"QUERY","title":"q","sql":"SELECT 1"}]}'
    draft = parse_workflow_draft(raw)
    assert draft is not None
    assert len(draft["nodes"]) == 1
    assert draft["nodes"][0]["type"] == "QUERY"
    assert "SELECT 1" in draft["nodes"][0]["sql"]


def test_multi_govern_flattened_to_single_query() -> None:
    raw = """
    {
      "name": "g",
      "nodes": [
        {"id": "n1", "type": "GOVERN", "title": "a", "sql": "SELECT id FROM emp"},
        {"id": "n2", "type": "QUERY", "title": "b", "sql": "SELECT * FROM __node_n1__"}
      ]
    }
    """
    draft = parse_workflow_draft(raw)
    assert draft is not None
    assert len(draft["nodes"]) == 1
    assert draft["nodes"][0]["type"] == "QUERY"
    assert draft["nodes"][0]["readonly"] is True
    sql = draft["nodes"][0]["sql"].lower()
    assert "__node_" not in sql
    assert "emp" in sql
