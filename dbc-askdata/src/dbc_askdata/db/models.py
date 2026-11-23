from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from dbc_askdata.config import get_settings
from dbc_askdata.db.session import Base

_SCHEMA = get_settings().database_schema


class AskProject(Base):
    __tablename__ = "ask_project"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    workspace_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_database: Mapped[str | None] = mapped_column(String(256))
    source_schema: Mapped[str | None] = mapped_column(String(256))
    work_connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    work_database: Mapped[str | None] = mapped_column(String(256))
    work_schema: Mapped[str | None] = mapped_column(String(256))
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AskSession(Base):
    __tablename__ = "ask_session"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(256))
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", server_default="ACTIVE")
    # 遗留列：事实卡/摘要逻辑已移除，仅保留 schema 兼容，禁止业务读写
    fact_card: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    conversation_summary: Mapped[str | None] = mapped_column(Text)
    summary_message_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AskVerifiedSample(Base):
    """用户确认 SQL 正确后的轻量样本：只存 workflowId，表名用时解析。"""

    __tablename__ = "ask_verified_sample"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    hitl_resolution: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    run_id: Mapped[int | None] = mapped_column(BigInteger)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AskRunFeedback(Base):
    """画布执行成功后的有用/无用/保存记忆，按 run+user 幂等。"""

    __tablename__ = "ask_run_feedback"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    useful_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    useless_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    memory_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    sample_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AskMessage(Base):
    __tablename__ = "ask_message"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="text", server_default="text")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AskHitl(Base):
    __tablename__ = "ask_hitl"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", server_default="PENDING")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskHitlCard(Base):
    """HITL 确认卡片：resolve 落草稿，有用/记忆时归并进意图表或 METADATA 字段字典。"""

    __tablename__ = "ask_hitl_card"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hitl_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger)
    connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    database_name: Mapped[str | None] = mapped_column(String(256))
    schema_name: Mapped[str | None] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_table: Mapped[str | None] = mapped_column(String(256))
    target_column: Mapped[str | None] = mapped_column(String(256))
    target_value: Mapped[str | None] = mapped_column(Text)
    question: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    promote_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskWorkflowDraft(Base):
    __tablename__ = "ask_workflow_draft"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    nodes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AskWorkflow(Base):
    __tablename__ = "ask_workflow"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    nodes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AskWorkflowRun(Base):
    __tablename__ = "ask_workflow_run"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", server_default="PENDING")
    result_table_fqn: Mapped[str | None] = mapped_column(String(256))
    cancel_token: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class AskWorkflowRunNode(Base):
    __tablename__ = "ask_workflow_run_node"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", server_default="PENDING")
    sql_text: Mapped[str | None] = mapped_column(Text)
    temp_table_fqn: Mapped[str | None] = mapped_column(String(256))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskWorkflowRunLog(Base):
    __tablename__ = "ask_workflow_run_log"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO", server_default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AskWorkflowRunResult(Base):
    __tablename__ = "ask_workflow_run_result"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    columns_json: Mapped[list[Any] | None] = mapped_column(JSONB)
    rows_json: Mapped[list[Any] | None] = mapped_column(JSONB)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AskTurn(Base):
    """一次问数（用户一轮提问）头表；监控列表读此表，span 按下钻。"""

    __tablename__ = "ask_turn"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    root_trace_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING", server_default="RUNNING")
    workspace_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    hitl_id: Mapped[int | None] = mapped_column(BigInteger)
    route: Mapped[str | None] = mapped_column(String(16))
    token_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    token_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    span_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(String(1024))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskWorkLog(Base):
    """问数进度工作日志：按 turn 持久化，工作台按轮次回看。"""

    __tablename__ = "ask_work_log"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    turn_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    seq: Mapped[int | None] = mapped_column(BigInteger)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO", server_default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AskLlmSpan(Base):
    __tablename__ = "ask_llm_span"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    span_key: Mapped[str | None] = mapped_column(String(36), index=True)
    parent_span_key: Mapped[str | None] = mapped_column(String(36), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    turn_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    parent_span_id: Mapped[int | None] = mapped_column(BigInteger)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    run_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    residency: Mapped[str | None] = mapped_column(String(16))
    model: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="OK", server_default="OK")
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    token_in: Mapped[int | None] = mapped_column(Integer)
    token_out: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(1024))
    payload_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskKnowledgeBinding(Base):
    """连接/库/模式 → ada-memory 文档绑定，供问数按作用域取 document_id。"""

    __tablename__ = "ask_knowledge_binding"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger)
    connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    connection_name: Mapped[str | None] = mapped_column(String(256))
    database_name: Mapped[str | None] = mapped_column(String(256))
    schema_name: Mapped[str | None] = mapped_column(String(256))
    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_name: Mapped[str | None] = mapped_column(String(256))
    knowledge_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    involved_tables: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)
    remark: Mapped[str | None] = mapped_column(String(512))
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AskDocument(Base):
    """问数文档：源文件元数据与 Markdown。原件在 DOCUMENTS_DIR。"""

    __tablename__ = "ask_document"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_relpath: Mapped[str] = mapped_column(String(1024), nullable=False)
    pipeline: Mapped[str] = mapped_column(String(16), nullable=False)
    convert_status: Mapped[str] = mapped_column(String(16), nullable=False, default="QUEUED", server_default="QUEUED")
    convert_error: Mapped[str | None] = mapped_column(Text)
    markdown: Mapped[str | None] = mapped_column(Text)
    markdown_from_convert: Mapped[str | None] = mapped_column(Text)
    markdown_edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    knowledge_document_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AskTableRelationBinding(Base):
    """连接/库/模式 → ada-graph 图谱绑定，供 SQL 生成查表关联路径。"""

    __tablename__ = "ask_table_relation_binding"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger)
    connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    connection_name: Mapped[str | None] = mapped_column(String(256))
    database_name: Mapped[str | None] = mapped_column(String(256))
    schema_name: Mapped[str | None] = mapped_column(String(256))
    graph_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    graph_name: Mapped[str | None] = mapped_column(String(256))
    remark: Mapped[str | None] = mapped_column(String(512))
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class AskUserTokenDaily(Base):
    __tablename__ = "ask_user_token_daily"
    __table_args__ = {"schema": _SCHEMA}

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AskIdempotency(Base):
    __tablename__ = "ask_idempotency"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    route: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="RUNNING", server_default="RUNNING")
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AskGraphCheckpoint(Base):
    __tablename__ = "ask_graph_checkpoint"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    hitl_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String(16), default="INTERRUPTED", server_default="INTERRUPTED")
    interrupted_node: Mapped[str | None] = mapped_column(String(64))
    resume_from: Mapped[str | None] = mapped_column(String(64))
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AskAppConfig(Base):
    """系统管理 · 应用配置（按 module 存 JSON）。"""

    __tablename__ = "ask_app_config"
    __table_args__ = {"schema": _SCHEMA}

    module: Mapped[str] = mapped_column(String(64), primary_key=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
