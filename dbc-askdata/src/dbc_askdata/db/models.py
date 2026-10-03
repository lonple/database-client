from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
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


class AskLlmSpan(Base):
    __tablename__ = "ask_llm_span"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
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


class AskKnowledge(Base):
    """问数知识索引：类型 + 切片规则 + 元数据过滤字段 + memory 文章 id。"""

    __tablename__ = "ask_knowledge"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    knowledge_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    slice_logic: Mapped[str] = mapped_column(String(32), nullable=False, default="AI_SUGGEST", server_default="AI_SUGGEST")
    slice_rule: Mapped[str | None] = mapped_column(Text)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger)
    connection_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    database_name: Mapped[str | None] = mapped_column(String(256))
    schema_name: Mapped[str | None] = mapped_column(String(256))
    connection_name: Mapped[str | None] = mapped_column(String(256))
    db_type: Mapped[str | None] = mapped_column(String(64))
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
