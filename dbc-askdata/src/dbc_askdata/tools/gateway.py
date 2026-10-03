from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.knowledge.general_knowledge import search_catalog_directory_knowledge
from dbc_askdata.knowledge.table_knowledge import search_table_knowledge
from dbc_askdata.tools.registry import ToolDecl, ToolRegistry


class ListConnectionsArgs(BaseModel):
    workspace_id: int = Field(..., description="工作空间 ID")


class SearchCatalogArgs(BaseModel):
    workspace_id: int
    connection_id: int
    keyword: str | None = None
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    page: int = 1
    size: int = 50

    model_config = {"populate_by_name": True}


class DescribeTableArgs(BaseModel):
    workspace_id: int
    connection_id: int
    table: str
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class GetColumnProfileArgs(BaseModel):
    workspace_id: int
    connection_id: int
    table: str
    column: str
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    top_n: int | None = Field(
        default=None,
        description="返回频次最高的取值条数上限；默认服务端配置",
    )

    model_config = {"populate_by_name": True}


class SampleColumnsArgs(BaseModel):
    workspace_id: int
    connection_id: int
    table: str
    columns: list[str] = Field(..., min_length=1)
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    max_rows: int = 20

    model_config = {"populate_by_name": True}


class ExplainSqlArgs(BaseModel):
    workspace_id: int
    connection_id: int
    sql: str
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


def _ident(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"非法标识符: {name}")
    return name


def _fq_table(schema: str | None, table: str) -> str:
    t = _ident(table)
    if schema:
        return f"{_ident(schema)}.{t}"
    return t


def _first_statement(exec_data: dict[str, Any] | None) -> dict[str, Any]:
    stmts = (exec_data or {}).get("statements") or []
    if not stmts:
        return {}
    return stmts[0] if isinstance(stmts[0], dict) else {}


def _cell(row: Any, idx: int) -> Any:
    if isinstance(row, (list, tuple)) and len(row) > idx:
        return row[idx]
    if isinstance(row, dict):
        vals = list(row.values())
        return vals[idx] if idx < len(vals) else None
    return None


def build_column_profile(
    *,
    table: str,
    column: str,
    schema: str | None,
    stats_exec: dict[str, Any] | None,
    values_exec: dict[str, Any] | None,
    enum_max_distinct: int,
) -> dict[str, Any]:
    """将 sqlwork execute 结果规整为列画像（含枚举值频次）。"""
    stats = _first_statement(stats_exec)
    if stats.get("success") is False:
        raise RuntimeError(stats.get("message") or "列画像聚合失败")
    srow = (stats.get("rows") or [None])[0]
    row_count = int(_cell(srow, 0) or 0) if srow is not None else 0
    distinct_count = int(_cell(srow, 1) or 0) if srow is not None else 0
    null_count = int(_cell(srow, 2) or 0) if srow is not None else 0

    values_stmt = _first_statement(values_exec)
    value_counts: list[dict[str, Any]] = []
    if values_stmt.get("success") is not False:
        for row in values_stmt.get("rows") or []:
            value_counts.append(
                {
                    "value": _cell(row, 0),
                    "count": int(_cell(row, 1) or 0),
                }
            )

    enum_like = distinct_count > 0 and distinct_count <= enum_max_distinct
    return {
        "table": table,
        "schema": schema,
        "column": column,
        "row_count": row_count,
        "distinct_count": distinct_count,
        "null_count": null_count,
        "enum_like": enum_like,
        "value_counts": value_counts,
        "note": (
            "低基数列，value_counts 可用于 WHERE/分组的真实码值"
            if enum_like
            else "高基数列，仅返回频次 TopN，勿当作完整枚举"
        ),
    }


def build_tool_registry(settings: Settings, sqlwork: SqlworkClient) -> ToolRegistry:
    registry = ToolRegistry()

    async def list_connections(args: dict[str, Any]) -> Any:
        return await sqlwork.list_connections(args["workspace_id"])

    async def search_catalog(args: dict[str, Any]) -> Any:
        tables = await sqlwork.list_tables(
            args["workspace_id"],
            args["connection_id"],
            database=args.get("database"),
            schema=args.get("schema_name"),
            keyword=args.get("keyword"),
            page=args.get("page") or 1,
            size=min(int(args.get("size") or 50), 100),
        )
        # 旁路 GENERAL 切片：schema/database +「库表目录」，topK=1；失败不阻断目录
        knowledge = await search_catalog_directory_knowledge(
            settings,
            database=args.get("database"),
            schema=args.get("schema_name"),
        )
        if isinstance(tables, dict):
            out = dict(tables)
            out["knowledge"] = knowledge
            return out
        return {"items": tables or [], "knowledge": knowledge}

    async def describe_table(args: dict[str, Any]) -> Any:
        columns = await sqlwork.list_columns(
            args["workspace_id"],
            args["connection_id"],
            table=args["table"],
            database=args.get("database"),
            schema=args.get("schema_name"),
        )
        knowledge = await search_table_knowledge(
            settings,
            connection_id=int(args["connection_id"]),
            database=args.get("database"),
            schema=args.get("schema_name"),
            table=str(args.get("table") or ""),
            top_k=1,
        )
        return {
            "columns": columns,
            "knowledge": knowledge,
        }

    async def get_column_profile(args: dict[str, Any]) -> Any:
        """列画像 + 枚举值频次；由模型在需要码值时主动调用。"""
        schema = args.get("schema_name")
        table = args["table"]
        col = _ident(args["column"])
        fq = _fq_table(schema, table)
        top_n = min(
            int(args.get("top_n") or settings.profile_enum_top_n),
            max(1, settings.profile_enum_top_n),
        )
        # 可移植聚合：避免依赖 PG 专属 FILTER 语法
        stats_sql = (
            f"SELECT COUNT(*) AS cnt, "
            f"COUNT(DISTINCT {col}) AS distinct_cnt, "
            f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS null_cnt "
            f"FROM {fq}"
        )
        values_sql = (
            f"SELECT {col} AS value, COUNT(*) AS cnt "
            f"FROM {fq} "
            f"WHERE {col} IS NOT NULL "
            f"GROUP BY {col} "
            f"ORDER BY COUNT(*) DESC "
            f"LIMIT {top_n}"
        )
        stats_exec = await sqlwork.execute(
            workspace_id=args["workspace_id"],
            connection_id=args["connection_id"],
            sql=stats_sql,
            max_rows=10,
            database=args.get("database"),
            schema=schema,
        )
        values_exec = await sqlwork.execute(
            workspace_id=args["workspace_id"],
            connection_id=args["connection_id"],
            sql=values_sql,
            max_rows=top_n,
            database=args.get("database"),
            schema=schema,
        )
        return build_column_profile(
            table=table,
            column=col,
            schema=schema,
            stats_exec=stats_exec,
            values_exec=values_exec,
            enum_max_distinct=settings.profile_enum_max_distinct,
        )

    async def sample_columns(args: dict[str, Any]) -> Any:
        cols = args["columns"][: settings.sample_max_columns]
        if not cols:
            raise ValueError("columns 不能为空")
        col_sql = ", ".join(_ident(c) for c in cols)
        table = _fq_table(args.get("schema_name"), args["table"])
        max_rows = min(int(args.get("max_rows") or settings.sample_max_rows), settings.sample_max_rows)
        sql = f"SELECT {col_sql} FROM {table} LIMIT {max_rows}"
        return await sqlwork.execute(
            workspace_id=args["workspace_id"],
            connection_id=args["connection_id"],
            sql=sql,
            max_rows=max_rows,
            database=args.get("database"),
            schema=args.get("schema_name"),
        )

    async def explain_sql(args: dict[str, Any]) -> Any:
        raw = (args.get("sql") or "").strip().rstrip(";")
        if not raw or ";" in raw:
            raise ValueError("explain_sql 仅允许单条语句")
        upper = raw.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH") or upper.startswith("EXPLAIN")):
            raise ValueError("explain_sql 仅允许只读 SELECT/WITH")
        if upper.startswith("EXPLAIN"):
            sql = raw
        else:
            sql = f"EXPLAIN {raw}"
        return await sqlwork.execute(
            workspace_id=args["workspace_id"],
            connection_id=args["connection_id"],
            sql=sql,
            max_rows=200,
            database=args.get("database"),
            schema=args.get("schema_name"),
        )

    registry.register(
        ToolDecl(
            name="list_connections",
            description="列出工作空间已授权连接",
            parameters_model=ListConnectionsArgs,
            handler=list_connections,
        )
    )
    registry.register(
        ToolDecl(
            name="search_catalog",
            description=(
                "按关键字检索表/视图；并附带当前库/模式下「库表目录」相关知识切片（若有，最多 1 条）"
            ),
            parameters_model=SearchCatalogArgs,
            handler=search_catalog,
        )
    )
    registry.register(
        ToolDecl(
            name="describe_table",
            description=(
                "查看表列结构（名称/类型/注释），并附带该连接/库/模式下元数据知识库中"
                "与表名相关的切片（业务说明/表注释等，若有）。"
                "拿到 knowledge 后须再核对表业务含义是否匹配用户问题；不符则换表重探"
            ),
            parameters_model=DescribeTableArgs,
            handler=describe_table,
        )
    )
    registry.register(
        ToolDecl(
            name="get_column_profile",
            description=(
                "列画像与枚举值频次统计：返回 row_count/distinct_count/null_count、"
                "enum_like、value_counts[{value,count}]。"
                "当 WHERE/分组可能依赖状态、类型、性别、码表等离散取值时再调用；"
                "SQL 必须使用 value_counts 中的真实码值，禁止用自然语言猜测。"
            ),
            parameters_model=GetColumnProfileArgs,
            handler=get_column_profile,
        )
    )
    registry.register(
        ToolDecl(
            name="explain_sql",
            description="对只读 SQL 执行 EXPLAIN",
            parameters_model=ExplainSqlArgs,
            handler=explain_sql,
        )
    )
    if settings.sample_tool_enabled():
        registry.register(
            ToolDecl(
                name="sample_columns",
                description="采样指定列（仅 local residency）",
                parameters_model=SampleColumnsArgs,
                handler=sample_columns,
                enabled=True,
            )
        )
    return registry
