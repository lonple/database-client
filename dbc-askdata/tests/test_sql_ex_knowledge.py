from dbc_askdata.knowledge.sql_ex_knowledge import format_sql_ex_knowledge_for_prompt


def test_format_sql_ex_knowledge():
    payload = format_sql_ex_knowledge_for_prompt(
        [
            {
                "documentId": 1,
                "title": "SQL关键字空格示例",
                "body": "禁止 cntFROM，应写 cnt FROM",
            }
        ]
    )
    assert payload is not None
    assert payload["category"] == "SQL_EX"
    assert payload["examples"][0]["title"] == "SQL关键字空格示例"
    assert "cntFROM" in payload["examples"][0]["content"]
    assert "instruction" in payload


def test_format_empty():
    assert format_sql_ex_knowledge_for_prompt([]) is None
    assert format_sql_ex_knowledge_for_prompt(None) is None
