from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from dbc_askdata.config import get_settings
from dbc_askdata.db.session import Base

_SCHEMA = get_settings().database_schema


class EvalTemplate(Base):
    __tablename__ = "eval_template"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="v1")
    remark: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvalProject(Base):
    __tablename__ = "eval_project"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(512))
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_database: Mapped[str | None] = mapped_column(String(128))
    source_schema: Mapped[str | None] = mapped_column(String(128))
    work_connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    work_database: Mapped[str | None] = mapped_column(String(128))
    work_schema: Mapped[str | None] = mapped_column(String(128))
    ask_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvalCase(Base):
    __tablename__ = "eval_case"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    template_id: Mapped[int | None] = mapped_column(BigInteger)
    project_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    govern_subtype: Mapped[str | None] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expect_sql: Mapped[str | None] = mapped_column(Text)
    compare_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    compare_spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    hitl_replies_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)
    tags_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)
    difficulty: Mapped[int | None] = mapped_column(SmallInteger)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvalTask(Base):
    __tablename__ = "eval_task"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PENDING")
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvalTaskCase(Base):
    __tablename__ = "eval_task_case"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    case_id: Mapped[int | None] = mapped_column(BigInteger)
    case_key: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expect_sql: Mapped[str | None] = mapped_column(Text)
    compare_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    compare_spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    govern_subtype: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(64))
    hitl_replies_json: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PENDING")
    ask_sql: Mapped[str | None] = mapped_column(Text)
    ask_error: Mapped[str | None] = mapped_column(Text)
    hitl_rounds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    compare_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    compare_detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    expect_row_count: Mapped[int | None] = mapped_column(Integer)
    ask_row_count: Mapped[int | None] = mapped_column(Integer)
    trace_id: Mapped[str | None] = mapped_column(String(64))
    workflow_id: Mapped[int | None] = mapped_column(BigInteger)
    run_id: Mapped[int | None] = mapped_column(BigInteger)
    session_id: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
