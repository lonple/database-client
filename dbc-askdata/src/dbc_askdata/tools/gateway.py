from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.knowledge.table_catalog_search import search_catalog_candidate_tables
from dbc_askdata.knowledge.table_knowledge import search_table_knowledge
from dbc_askdata.tools.registry import ToolDecl, ToolRegistry

log = logging.getLogger(__name__)


def _describe_cache_parts(
    *,
    connection_id: Any,
    database: str | None,
    schema_name: str | None,
    table: str,
) -> tuple[str, ...]:
    return (
        "tool",
        "describe",
        str(connection_id),
        str(database or ""),
        str(schema_name or ""),
        str(table or ""),
    )


async def describe_tables_batch(
    settings: Settings,
    sqlwork: SqlworkClient,
    *,
    workspace_id: int,
    connection_id: int,
    tables: list[str],
    database: str | None = None,
    schema_name: str | None = None,
) -> dict[str, dict[str, Any]]:
    """多表 describe：sqlwork 列批查 + 表知识并行；返回 table_name -> {columns, knowledge, __cache__}。"""
    from dbc_askdata.redis.client import get_redis

    names: list[str] = []
    seen: set[str] = set()
    for raw in tables:
        t = str(raw or "").strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(t)
        if len(names) >= 20:
            break
    if not names:
        return {}

    redis = get_redis()
    out: dict[str, dict[str, Any]] = {}
    miss: list[str] = []
    for t in names:
        parts = _describe_cache_parts(
            connection_id=connection_id,
            database=database,
            schema_name=schema_name,
            table=t,
        )
        if redis is not None:
            cached = await redis.get_json(*parts)
            if isinstance(cached, dict):
                hit = dict(cached)
                hit["__cache__"] = "hit"
                out[t] = hit
                continue
        miss.append(t)

    if not miss:
        return out

    try:
        batch_rows = await sqlwork.list_columns_batch(
            workspace_id,
            connection_id,
            tables=miss,
            database=database,
            schema=schema_name,
        )
    except Exception:
        log.error(
            "批量列查询失败 connection_id=%s tables=%s，回退单表",
            connection_id,
            miss,
            exc_info=True,
        )
        batch_rows = []

    cols_by_table: dict[str, list[dict[str, Any]]] = {}
    err_by_table: dict[str, str] = {}
    for row in batch_rows:
        if not isinstance(row, dict):
            continue
        tname = str(row.get("table") or "").strip()
        if not tname:
            continue
        if row.get("error"):
            err_by_table[tname] = str(row.get("error"))
            cols_by_table[tname] = []
        else:
            cols = row.get("columns")
            cols_by_table[tname] = cols if isinstance(cols, list) else []

    # 批接口未覆盖的表：单表回退
    for t in miss:
        if t in cols_by_table or t in err_by_table:
            continue
        try:
            cols_by_table[t] = await sqlwork.list_columns(
                workspace_id,
                connection_id,
                table=t,
                database=database,
                schema=schema_name,
            )
        except Exception as ex:
            log.warning("单表列查询失败 table=%s", t, exc_info=True)
            err_by_table[t] = str(ex)
            cols_by_table[t] = []

    async def _kg(t: str) -> tuple[str, dict[str, Any]]:
        try:
            kg = await search_table_knowledge(
                settings,
                connection_id=connection_id,
                database=database,
                schema=schema_name,
                table=t,
                top_k=1,
            )
            return t, kg if isinstance(kg, dict) else {}
        except Exception:
            log.warning("批量 describe 知识检索失败 table=%s", t, exc_info=True)
            return t, {}

    kg_pairs = await asyncio.gather(*[_kg(t) for t in miss])
    kg_by_table = dict(kg_pairs)

    for t in miss:
        payload: dict[str, Any] = {
            "columns": cols_by_table.get(t) or [],
            "knowledge": kg_by_table.get(t) or {},
        }
        if t in err_by_table and not payload["columns"]:
            payload["error"] = err_by_table[t]
        if redis is not None and payload.get("columns"):
            await redis.set_json(
                *_describe_cache_parts(
                    connection_id=connection_id,
                    database=database,
                    schema_name=schema_name,
                    table=t,
                ),
                value={k: v for k, v in payload.items() if k != "__cache__"},
                ttl_seconds=settings.tool_cache_ttl_seconds,
            )
            payload["__cache__"] = "set"
        else:
            payload["__cache__"] = "disabled" if redis is None else "skip"
        out[t] = payload
    return out


class ListConnectionsArgs(BaseModel):
    workspace_id: int = Field(..., description="工作空间 ID")


class SearchCatalogArgs(BaseModel):
    workspace_id: int
    connection_id: int
    keyword: str = Field(
        ...,
        description="中文业务表意/所需表的中文描述（语义检索用），不要只填英文物理表名",
    )
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    page: int = 1
    size: int = 5

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
    condition_value: str | None = Field(
        default=None,
        alias="conditionValue",
        description="用户条件原词。传入后返回 action，不要求该值出现在 value_counts",
    )
    column_comment: list[dict[str, str]] | str | None = Field(
        default=None,
        alias="columnComment",
        description=(
            "模型从 describe 字段说明中拆好的字典，禁止传原文。"
            "优先 [{key,value},...]，例如 [{key:planning,value:规划中}]；"
            "或规范化串 planning=规划中;active=进行中。无码表则省略本参数。"
        ),
    )
    hop: int | None = Field(default=0, description="同一条件沿外键重选的次数，从 0 开始，达到 3 则 HITL")

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


class ListTableRelationsArgs(BaseModel):
    workspace_id: int
    connection_id: int
    table: str = Field(..., description="物理表名（不含 schema）")
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    max_depth: int | None = Field(default=1, alias="maxDepth", description="邻接跳数 1..3")

    model_config = {"populate_by_name": True}


class QueryTableRelationsArgs(BaseModel):
    workspace_id: int
    connection_id: int
    from_table: str = Field(..., alias="fromTable", description="起点物理表名（不含 schema）")
    to_table: str = Field(..., alias="toTable", description="终点物理表名（不含 schema）")
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    max_depth: int | None = Field(default=6, alias="maxDepth", description="最大跳数 1..8")

    model_config = {"populate_by_name": True}


def _ident(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"非法标识符: {name}")
    return name


def _split_schema_table(
    table: str,
    schema: str | None = None,
) -> tuple[str | None, str]:
    """允许模型误传 schema.table：拆成 (schema, bare_table)。"""
    raw = (table or "").strip().strip('"').strip("`")
    sch = (schema or "").strip() or None
    if "." in raw:
        parts = [p.strip() for p in raw.split(".") if p.strip()]
        if len(parts) >= 2:
            return (parts[-2], parts[-1])
        raw = parts[-1] if parts else raw
    return sch, raw


def _fq_table(schema: str | None, table: str) -> str:
    sch, bare = _split_schema_table(table, schema)
    t = _ident(bare)
    if sch:
        return f"{_ident(sch)}.{t}"
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
        """语义检索知识库测表切片：只返回候选表名 + 表描述（top 5，不改写）。"""
        keyword = (args.get("keyword") or "").strip()
        top_k = min(int(args.get("size") or 5), 5)
        result = await search_catalog_candidate_tables(
            settings,
            connection_id=int(args["connection_id"]),
            database=args.get("database"),
            schema=args.get("schema_name"),
            query=keyword,
            top_k=top_k,
        )
        return {
            "items": result.get("items") or [],
            "query": result.get("query") or keyword,
            "documentIds": result.get("documentIds") or [],
        }

    async def describe_table(args: dict[str, Any]) -> Any:
        sch, bare = _split_schema_table(
            str(args.get("table") or "").strip(),
            args.get("schema_name") or args.get("schema"),
        )
        batch = await describe_tables_batch(
            settings,
            sqlwork,
            workspace_id=int(args["workspace_id"]),
            connection_id=int(args["connection_id"]),
            tables=[bare],
            database=args.get("database"),
            schema_name=sch,
        )
        out = batch.get(bare)
        if out is None:
            # 大小写不一致时兜底取唯一结果
            if len(batch) == 1:
                return next(iter(batch.values()))
            return {"columns": [], "knowledge": {}, "__cache__": "disabled"}
        return out

    async def get_column_profile(args: dict[str, Any]) -> Any:
        """列画像。有字典说明时只做 value→key；否则用 Top 样本判断格式是否与条件同类。"""
        from dbc_askdata.redis.client import get_redis
        from dbc_askdata.verify.condition_match import (
            format_decision,
            fk_targets,
            match_dictionary,
            mismatch_action,
            normalize_dictionary_pairs,
        )

        condition = str(args.get("condition_value") or args.get("conditionValue") or "").strip()
        hop = int(args.get("hop") or 0)
        pairs = normalize_dictionary_pairs(
            args.get("column_comment")
            if args.get("column_comment") is not None
            else args.get("columnComment")
        )
        if pairs:
            if not condition:
                return {
                    "dictionary": True,
                    "action": "need_condition",
                    "pairs": [{"key": key, "value": value} for key, value in pairs],
                    "message": "这是字典字段。请带上 condition_value 再调用，不要先查画像。",
                }
            exact = match_dictionary(condition, pairs)
            if exact.get("action") != "need_similarity":
                return exact
            try:
                from dbc_askdata.llm.client import LlmClient

                vectors = await LlmClient(settings).embed_texts(
                    [condition, *[value for _, value in pairs]]
                )
            except Exception:
                log.warning(
                    "字典 value 余弦计算失败 table=%s column=%s",
                    args.get("table"),
                    args.get("column"),
                    exc_info=True,
                )
                return {
                    "action": "hitl",
                    "dictionary": True,
                    "reason": "字典 value 余弦相似度计算失败",
                    "values": [value for _, value in pairs],
                }
            from dbc_askdata.verify.condition_match import match_dictionary_cosine

            return match_dictionary_cosine(
                pairs,
                vectors[0],
                vectors[1:],
                threshold=float(settings.dict_cosine_threshold),
            )

        schema, table = _split_schema_table(
            str(args.get("table") or ""),
            args.get("schema_name") or args.get("schema"),
        )
        # 写回规范化参数，后续 FK/缓存与进度展示用裸表名
        args["table"] = table
        if schema:
            args["schema_name"] = schema
            args["schema"] = schema
        try:
            col = _ident(str(args.get("column") or ""))
        except ValueError:
            return {
                "error": f"非法列名: {args.get('column')}",
                "hint": "column 只传物理列名；若列不存在，请改用 describe_table 返回的真实列，勿对同一表反复 describe。",
            }
        cache_parts = (
            "tool",
            "profile",
            str(args.get("connection_id")),
            str(args.get("database") or ""),
            str(schema or ""),
            str(table),
            col,
        )
        redis = get_redis()
        if redis is not None:
            cached = await redis.get_json(*cache_parts)
            if isinstance(cached, dict):
                hit = dict(cached)
                hit["__cache__"] = "hit"
                if condition:
                    hit.update(await _profile_condition_action(args, hit, condition, hop))
                return hit
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
        out = build_column_profile(
            table=table,
            column=col,
            schema=schema,
            stats_exec=stats_exec,
            values_exec=values_exec,
            enum_max_distinct=settings.profile_enum_max_distinct,
        )
        if redis is not None:
            await redis.set_json(
                *cache_parts,
                value=out,
                ttl_seconds=settings.tool_cache_ttl_seconds,
            )
            out = {**out, "__cache__": "set"}
        else:
            out = {**out, "__cache__": "disabled"}
        if condition:
            out.update(await _profile_condition_action(args, out, condition, hop))
        return out

    async def _profile_condition_action(
        profile_args: dict[str, Any],
        profile: dict[str, Any],
        condition: str,
        hop: int,
    ) -> dict[str, Any]:
        from dbc_askdata.verify.condition_match import (
            format_decision,
            fk_targets,
            mismatch_action,
        )

        samples = [
            row.get("value")
            for row in (profile.get("value_counts") or [])
            if isinstance(row, dict)
        ][:30]
        decision = format_decision(condition, samples)
        if decision.get("action") == "use_literal":
            return decision
        relations: list[dict[str, Any]] = []
        try:
            related = await list_table_relations(profile_args)
            if isinstance(related, dict):
                raw_rels = related.get("tableRelations") or []
                relations = [r for r in raw_rels if isinstance(r, dict)]
        except Exception:
            log.warning(
                "画像格式不一致时查询外键失败 table=%s column=%s",
                profile_args.get("table"),
                profile_args.get("column"),
                exc_info=True,
            )
        targets = fk_targets(
            str(profile_args.get("table") or ""),
            str(profile_args.get("column") or ""),
            relations,
        )
        return mismatch_action(
            hop=hop,
            targets=targets,
            column_format_name=str(decision.get("columnFormat") or ""),
            condition_format_name=str(decision.get("conditionFormat") or ""),
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

    async def list_table_relations(args: dict[str, Any]) -> Any:
        """按一张表查外键邻居。知识库再调图谱，返回 edges。"""
        from dbc_askdata.clients.ada_graph import AdaGraphClient
        from dbc_askdata.clients.ada_memory import AdaMemoryClient

        table = str(args.get("table") or "").strip()
        if "." in table:
            table = table.rsplit(".", 1)[-1]
        if not table:
            raise ValueError("list_table_relations 需要 table")
        graph_id = await AdaGraphClient(settings).resolve_id()
        if graph_id is None:
            return {
                "bound": False,
                "table": table,
                "tableRelations": [],
                "message": "默认知识图谱不存在",
            }
        depth = int(args.get("max_depth") or args.get("maxDepth") or 1)
        data = await AdaMemoryClient(settings).list_table_relations(
            graph_id=int(graph_id),
            table=table,
            max_depth=max(1, min(depth, 3)),
        )
        if isinstance(data, dict):
            data["bound"] = True
            data["graphId"] = int(graph_id)
        return data

    async def query_table_relations(args: dict[str, Any]) -> Any:
        """本地按连接/库/模式找图谱绑定，再查两表最短 JOIN 路径。失败重试一次后忽略。"""
        from dbc_askdata.clients.ada_graph import AdaGraphClient
        from dbc_askdata.clients.retry import with_one_retry
        import logging

        _log = logging.getLogger(__name__)

        from_table = str(args.get("from_table") or args.get("fromTable") or "").strip()
        to_table = str(args.get("to_table") or args.get("toTable") or "").strip()
        if not from_table or not to_table:
            raise ValueError("query_table_relations 需要 fromTable 与 toTable")
        # 允许 schema.table，工具内只取物理表名（图谱节点为表名）
        if "." in from_table:
            from_table = from_table.rsplit(".", 1)[-1]
        if "." in to_table:
            to_table = to_table.rsplit(".", 1)[-1]
        max_depth = int(args.get("max_depth") or args.get("maxDepth") or 6)

        async def _once() -> Any:
            graph = AdaGraphClient(settings)
            graph_id = await graph.resolve_id()
            if graph_id is None:
                return {"bound": False, "joins": [], "message": "默认知识图谱不存在"}
            data = await graph.table_join_path(
                graph_id=graph_id,
                from_table=from_table,
                to_table=to_table,
                max_depth=max_depth,
            )
            if isinstance(data, dict):
                data["bound"] = True
                data["graphId"] = graph_id
            return data

        try:
            return await with_one_retry("ada-graph table_join", _once)
        except Exception:
            _log.error(
                "知识图谱查询失败已忽略 from=%s to=%s",
                from_table,
                to_table,
                exc_info=True,
            )
            return {"ignored": True, "fromTable": from_table, "toTable": to_table, "path": None}

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
                "按中文业务表意语义检索知识库中的测表文档切片，返回候选表（仅 name=物理表名、"
                "description=表中文说明，最多 20 条）。keyword 须为中文所需表描述。"
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
                "确认条件字段。字典列：先由你从 describe 的 comment 拆成码表，"
                "再把拆好的 pairs 放进 column_comment（禁止传字段说明原文），并传 condition_value；"
                "action=use_key 用返回的 key；action=hitl 停止并请用户确认，不要再查画像。"
                "非字典列省略 column_comment：用 Top 样本判中文或编码。"
                "action=use_literal 直接用用户原词；action=follow_fk 到 targets 重选并 hop+1；"
                "action=retry_same_table 只在同表其他列重选。hop 达到 3 则 HITL。"
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
    registry.register(
        ToolDecl(
            name="list_table_relations",
            description=(
                "按一张物理表查询已配置图谱中的外键邻居。"
                "返回 tableRelations[].edges：fromTable/fromColumn/toTable/toColumn。"
                "上下文 table_relations 已有该表的边时不要调用。"
                "两张表都已确定、只缺 JOIN 路径时用 query_table_relations。"
            ),
            parameters_model=ListTableRelationsArgs,
            handler=list_table_relations,
        )
    )
    registry.register(
        ToolDecl(
            name="query_table_relations",
            description=(
                "查询两张业务表之间的关联路径（JOIN 列）。"
                "先按当前连接/库/模式查找已配置的库表关系图谱，再求最短路径。"
                "返回 joinTexts，形如「hr_employee.id 关联 att_daily_record.emp_id」。"
                "多表 JOIN 时应对每对需要关联的表调用；未配置图谱时 bound=false。"
            ),
            parameters_model=QueryTableRelationsArgs,
            handler=query_table_relations,
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
