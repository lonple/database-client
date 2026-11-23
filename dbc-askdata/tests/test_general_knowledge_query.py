from dbc_askdata.knowledge.general_knowledge import (
    build_catalog_directory_query,
    build_db_general_query,
)


def test_build_query_prefers_schema() -> None:
    assert build_db_general_query(database="postgres", schema="company") == "company 库通用知识"
    assert build_catalog_directory_query(database="postgres", schema="company") == "company 库表目录"


def test_build_query_falls_back_to_database() -> None:
    assert build_db_general_query(database="demo_db", schema=None) == "demo_db 库通用知识"
    assert build_db_general_query(database="demo_db", schema="  ") == "demo_db 库通用知识"
    assert build_catalog_directory_query(database="demo_db", schema=None) == "demo_db 库表目录"


def test_build_query_empty_scope() -> None:
    assert build_db_general_query(database=None, schema=None) is None
    assert build_db_general_query(database="", schema="") is None
    assert build_catalog_directory_query(database=None, schema=None) is None
