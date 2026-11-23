from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import (
    AskProject,
    AskWorkflow,
    AskWorkflowRun,
    AskWorkflowRunLog,
    AskWorkflowRunNode,
    AskWorkflowRunResult,
)
from dbc_askdata.db.scope import is_pg_style
from dbc_askdata.observability.spans import SpanRecorder, mark_run_inflight

log = logging.getLogger(__name__)

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(name: str) -> str:
    if not _IDENT.match(name or ""):
        raise ValueError(f"非法标识符: {name}")
    return name


def rewrite_node_refs(sql: str, outputs: dict[str, str]) -> str:
    """把上游节点引用改成实际临时表 FQN。支持 __node_n1__ 与 FROM/JOIN n1。"""
    if not sql or not outputs:
        return sql
    out = sql
    for nid, fqn in sorted(outputs.items(), key=lambda x: -len(x[0])):
        out = re.sub(rf"__node_{re.escape(nid)}__", fqn, out, flags=re.IGNORECASE)
        out = re.sub(
            rf'(?i)\b(FROM|JOIN)\s+"{re.escape(nid)}"',
            rf"\1 {fqn}",
            out,
        )
        out = re.sub(
            rf"(?i)\b(FROM|JOIN)\s+`{re.escape(nid)}`",
            rf"\1 {fqn}",
            out,
        )
        out = re.sub(
            rf"(?i)\b(FROM|JOIN)\s+{re.escape(nid)}\b",
            rf"\1 {fqn}",
            out,
        )
    return out


# FROM/JOIN 后紧跟的标识若为这些词，视为子句关键字而非表别名
_FROM_JOIN_ALIAS_BLOCKLIST = frozenset(
    {
        "WHERE",
        "GROUP",
        "ORDER",
        "LIMIT",
        "OFFSET",
        "HAVING",
        "UNION",
        "EXCEPT",
        "INTERSECT",
        "ON",
        "USING",
        "JOIN",
        "LEFT",
        "RIGHT",
        "FULL",
        "INNER",
        "CROSS",
        "NATURAL",
        "LATERAL",
        "AS",
        "SET",
        "RETURNING",
        "WINDOW",
        "FETCH",
        "FOR",
    }
)


def flatten_draft_to_inline_sql(draft: dict[str, Any] | None) -> str | None:
    """将多节点工作流展平为单条可执行 SQL（上游占位内联为子查询）。

    测评比对 / 与 expect_sql 同形态时使用；正常问数仍保留多节点 + ``__node_`` 占位。
    """
    if not draft:
        return None
    nodes = [n for n in (draft.get("nodes") or []) if isinstance(n, dict)]
    if not nodes:
        return None
    expanded: dict[str, str] = {}
    last: str | None = None
    for idx, n in enumerate(nodes):
        nid = str(n.get("id") or f"n{idx + 1}").strip() or f"n{idx + 1}"
        sql = (n.get("sql") or "").strip()
        if not sql:
            continue
        inline = expand_node_refs_for_explain(sql, expanded)
        expanded[nid] = inline
        last = inline
    return last


def draft_as_single_query(draft: dict[str, Any] | None) -> dict[str, Any] | None:
    """测评用：多节点草稿 → 单 QUERY 节点（SQL 已内联），便于执行与记录 ask_sql。"""
    if not draft:
        return None
    flat = flatten_draft_to_inline_sql(draft)
    if not flat:
        return None
    name = str(draft.get("name") or "问数工作流")[:128]
    return {
        "name": name,
        "nodes": [
            {
                "id": "n1",
                "type": "QUERY",
                "title": name,
                "sql": flat,
                "readonly": True,
            }
        ],
    }


def expand_node_refs_for_explain(sql: str, upstream_sql: dict[str, str]) -> str:
    """校验期把上游节点占位改写成子查询，便于 EXPLAIN（执行期仍用 rewrite_node_refs）。

    支持 ``__node_n1__`` 与 ``FROM/JOIN n1``。upstream_sql 的 value 应为已展开、无占位的 SQL。
    """
    if not sql or not upstream_sql:
        return sql
    block = "|".join(sorted(_FROM_JOIN_ALIAS_BLOCKLIST, key=len, reverse=True))
    out = sql
    for nid, usql in sorted(upstream_sql.items(), key=lambda x: -len(x[0])):
        body = (usql or "").strip().rstrip(";").strip()
        if not body:
            continue
        sub = f"({body})"

        def _placeholder_repl(match: re.Match[str], *, _sub: str = sub, _nid: str = nid) -> str:
            alias = match.group(1)
            if alias:
                return f"{_sub}{alias}"
            return f"{_sub} AS {_nid}"

        # 别名不得吞掉 WHERE/JOIN 等关键字
        out = re.sub(
            rf"__node_{re.escape(nid)}__(\s+(?:AS\s+)?(?!(?:{block})\b)[A-Za-z_][A-Za-z0-9_]*)?",
            _placeholder_repl,
            out,
            flags=re.IGNORECASE,
        )

        def _bare_repl(match: re.Match[str], *, _sub: str = sub, _nid: str = nid) -> str:
            kw = match.group(1)
            alias = match.group(2)
            if alias:
                return f"{kw} {_sub} {alias.strip()}"
            return f"{kw} {_sub} AS {_nid}"

        for quote in ('"', "`", ""):
            if quote:
                table = rf"{quote}{re.escape(nid)}{quote}"
            else:
                table = rf"{re.escape(nid)}\b"
            pat = (
                rf"(?i)\b(FROM|JOIN)\s+{table}"
                rf"(\s+(?:AS\s+)?(?!(?:{block})\b)[A-Za-z_][A-Za-z0-9_]*)?"
            )
            out = re.sub(pat, _bare_repl, out)
    return out

class WorkflowRunner:
    def __init__(self, settings: Settings, spans: SpanRecorder, work_db_type: str | None = None) -> None:
        self._settings = settings
        self._spans = spans
        self._work_db_type = work_db_type or "POSTGRESQL"

    async def start_run(
        self,
        session: AsyncSession,
        *,
        workflow: AskWorkflow,
        project: AskProject,
        sqlwork: SqlworkClient,
        user_id: int,
        session_id: int | None,
        trace_id: str | None,
        authorization: str,
        work_db_type: str | None = None,
    ) -> AskWorkflowRun:
        if not self._settings.allow_user_execute:
            raise ValueError("当前配置禁止用户执行工作流")
        if work_db_type:
            self._work_db_type = work_db_type
        cancel_token = uuid.uuid4().hex
        run = AskWorkflowRun(
            workflow_id=workflow.id,
            project_id=project.id,
            session_id=session_id,
            status="RUNNING",
            cancel_token=cancel_token,
            started_at=datetime.now(timezone.utc),
            owner_user_id=user_id,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        mark_run_inflight(1)
        try:
            await self._execute(session, run=run, workflow=workflow, project=project, sqlwork=sqlwork, trace_id=trace_id)
        except Exception as ex:
            log.warning("工作流执行失败 run_id=%s", run.id, exc_info=True)
            run.status = "FAILED"
            run.error_message = str(ex)[:2000]
            run.finished_at = datetime.now(timezone.utc)
            await self._log(session, run.id, "ERROR", f"执行失败: {ex}")
            await session.commit()
        finally:
            mark_run_inflight(-1)
        await session.refresh(run)
        return run

    async def stop(self, session: AsyncSession, run: AskWorkflowRun, sqlwork: SqlworkClient) -> AskWorkflowRun:
        if run.status not in ("RUNNING", "PENDING"):
            return run
        if run.cancel_token:
            try:
                await sqlwork.cancel(run.cancel_token)
            except Exception:
                log.warning("调用 sqlwork cancel 失败 run_id=%s", run.id, exc_info=True)
        run.status = "CANCELLED"
        run.finished_at = datetime.now(timezone.utc)
        await self._log(session, run.id, "WARN", "用户停止执行")
        await session.commit()
        await session.refresh(run)
        return run

    async def _execute(
        self,
        session: AsyncSession,
        *,
        run: AskWorkflowRun,
        workflow: AskWorkflow,
        project: AskProject,
        sqlwork: SqlworkClient,
        trace_id: str | None,
    ) -> None:
        nodes = (workflow.nodes_json or {}).get("nodes") or []
        if not nodes:
            raise ValueError("工作流无节点")
        work_conn = project.work_connection_id
        workspace_id = project.workspace_id
        last_result: dict[str, Any] | None = None
        result_fqn: str | None = None
        node_outputs: dict[str, str] = {}

        for idx, node in enumerate(nodes):
            await session.refresh(run)
            if run.status == "CANCELLED":
                await self._log(session, run.id, "WARN", "运行已取消，中止后续节点")
                return

            node_id = str(node.get("id") or f"n{idx}")
            node_type = str(node.get("type") or "QUERY").upper()
            sql = (node.get("sql") or "").strip()
            is_last = idx == len(nodes) - 1
            rn = AskWorkflowRunNode(
                run_id=run.id,
                node_id=node_id,
                node_type=node_type,
                status="RUNNING",
                sql_text=sql,
                started_at=datetime.now(timezone.utc),
            )
            session.add(rn)
            await session.commit()
            await self._log(session, run.id, "INFO", f"开始节点 {node_id} ({node_type})")

            try:
                if node_type not in ("QUERY", "SQL", "GOVERN"):
                    rn.status = "SKIPPED"
                    rn.finished_at = datetime.now(timezone.utc)
                    await session.commit()
                    await self._log(session, run.id, "INFO", f"跳过未知节点类型 {node_type}")
                    continue
                if not sql:
                    raise ValueError(f"节点 {node_id} 缺少 SQL")

                sql = rewrite_node_refs(sql, node_outputs)
                exec_sql = sql
                temp_fqn = None
                if node_type == "GOVERN" or (is_last and node_type in ("QUERY", "SQL")):
                    # GOVERN：中间临时表；末节点 QUERY：结果表
                    prefix = (
                        self._settings.result_table_prefix
                        if is_last and node_type != "GOVERN"
                        else self._settings.temp_table_prefix
                    )
                    table_name = _safe_ident(f"{prefix}{run.id}_{_safe_ident(node_id)}")
                    temp_fqn = self._fqn(project, table_name)
                    if self._settings.rerun_cleanup == "drop_then_recreate":
                        drop_sql = f"DROP TABLE IF EXISTS {temp_fqn}"
                        await self._exec(
                            sqlwork,
                            project,
                            drop_sql,
                            cancel_token=run.cancel_token,
                            max_rows=1,
                        )
                        # 内部运维步骤，不进用户可见执行日志（画布无对应节点）
                        await self._log(session, run.id, "DEBUG", f"清理旧表 {temp_fqn}")
                    exec_sql = self._wrap_ctas(temp_fqn, sql)
                    rn.temp_table_fqn = temp_fqn
                    if is_last and node_type != "GOVERN":
                        result_fqn = temp_fqn

                result = await self._exec(
                    sqlwork,
                    project,
                    exec_sql,
                    cancel_token=run.cancel_token,
                    max_rows=self._settings.workflow_run_row_limit,
                )
                last_result = result
                stmts = (result or {}).get("statements") or []
                ok = all(s.get("success", True) for s in stmts) if stmts else True
                if not ok:
                    msg = next((s.get("message") for s in stmts if not s.get("success")), "节点失败")
                    raise RuntimeError(msg)

                # 末结果若已落表，再读回摘要供弹窗
                if result_fqn and is_last:
                    preview = await self._exec(
                        sqlwork,
                        project,
                        f"SELECT * FROM {result_fqn}",
                        cancel_token=run.cancel_token,
                        max_rows=self._settings.workflow_run_row_limit,
                    )
                    last_result = preview

                rn.status = "SUCCESS"
                rn.finished_at = datetime.now(timezone.utc)
                if temp_fqn:
                    node_outputs[node_id] = temp_fqn
                await session.commit()
                await self._log(
                    session,
                    run.id,
                    "INFO",
                    f"节点 {node_id} 成功" + (f"；对象 {temp_fqn}" if temp_fqn else ""),
                )
                await self._spans.record(
                    session,
                    phase="execute",
                    kind="GRAPH",
                    name=node_id,
                    status="SUCCESS",
                    run_id=run.id,
                    project_id=project.id,
                    workspace_id=workspace_id,
                    trace_id=trace_id,
                    user_id=run.owner_user_id,
                    payload_meta={"temp_table_fqn": temp_fqn, "node_type": node_type},
                )
            except Exception as ex:
                rn.status = "FAILED"
                rn.error_message = str(ex)[:2000]
                rn.finished_at = datetime.now(timezone.utc)
                await session.commit()
                raise

        if last_result:
            stmts = last_result.get("statements") or []
            stmt = stmts[-1] if stmts else {}
            # 幂等覆盖结果摘要
            existing = (
                await session.execute(select(AskWorkflowRunResult).where(AskWorkflowRunResult.run_id == run.id))
            ).scalar_one_or_none()
            if existing:
                existing.columns_json = stmt.get("columns")
                existing.rows_json = stmt.get("rows")
                existing.row_count = int(stmt.get("rowCount") or 0)
                existing.truncated = bool(stmt.get("truncated"))
            else:
                session.add(
                    AskWorkflowRunResult(
                        run_id=run.id,
                        columns_json=stmt.get("columns"),
                        rows_json=stmt.get("rows"),
                        row_count=int(stmt.get("rowCount") or 0),
                        truncated=bool(stmt.get("truncated")),
                    )
                )

        run.status = "SUCCESS"
        run.result_table_fqn = result_fqn
        run.finished_at = datetime.now(timezone.utc)
        await self._log(session, run.id, "INFO", "工作流执行完成" + (f"；结果表 {result_fqn}" if result_fqn else ""))
        await session.commit()

    def _fqn(self, project: AskProject, table: str) -> str:
        if project.work_schema and is_pg_style(self._work_db_type):
            return f"{_safe_ident(project.work_schema)}.{table}"
        return table

    def _wrap_ctas(self, fqn: str, select_sql: str) -> str:
        sql = select_sql.strip().rstrip(";")
        upper = sql.upper()
        if upper.startswith("CREATE ") or upper.startswith("DROP ") or upper.startswith("INSERT "):
            # 已是 DDL/DML，直接在工作连接执行（仍须授权）
            return sql
        if is_pg_style(self._work_db_type):
            return f"CREATE TABLE {fqn} AS {sql}"
        # MySQL
        return f"CREATE TABLE {fqn} AS {sql}"

    async def _exec(
        self,
        sqlwork: SqlworkClient,
        project: AskProject,
        sql: str,
        *,
        cancel_token: str | None,
        max_rows: int,
    ) -> dict[str, Any]:
        exec_sql = sql
        # 同连接下来源/工作模式不同：每批语句前设置 search_path，避免未限定表名落到 work_schema
        if (
            is_pg_style(self._work_db_type)
            and project.work_schema
            and project.source_schema
            and project.work_schema != project.source_schema
            and project.work_connection_id == project.source_connection_id
            and not sql.strip().upper().startswith("SET ")
        ):
            sp = f"{_safe_ident(project.work_schema)}, {_safe_ident(project.source_schema)}"
            exec_sql = f"SET search_path TO {sp};\n{sql}"
        return await sqlwork.execute(
            workspace_id=project.workspace_id,
            connection_id=project.work_connection_id,
            sql=exec_sql,
            max_rows=max_rows,
            database=project.work_database,
            schema=project.work_schema,
            cancel_token=cancel_token,
        )

    async def _log(self, session: AsyncSession, run_id: int, level: str, message: str) -> None:
        session.add(AskWorkflowRunLog(run_id=run_id, level=level, message=message))
        await session.commit()


async def load_workflow(session: AsyncSession, workflow_id: int) -> AskWorkflow | None:
    return await session.get(AskWorkflow, workflow_id)


async def load_project(session: AsyncSession, project_id: int) -> AskProject | None:
    return await session.get(AskProject, project_id)


async def get_run(session: AsyncSession, run_id: int) -> AskWorkflowRun | None:
    return await session.get(AskWorkflowRun, run_id)


async def list_run_logs(session: AsyncSession, run_id: int) -> list[AskWorkflowRunLog]:
    result = await session.execute(
        select(AskWorkflowRunLog).where(AskWorkflowRunLog.run_id == run_id).order_by(AskWorkflowRunLog.id.asc())
    )
    return list(result.scalars().all())
