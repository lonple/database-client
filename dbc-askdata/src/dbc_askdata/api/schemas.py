from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    message: str = "ok"
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "ok") -> "ApiResponse":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "ApiResponse":
        return cls(success=False, message=message, data=data)


class ProjectCreateRequest(BaseModel):
    workspace_id: int = Field(..., alias="workspaceId")
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    # 数据来源（探测/生成默认作用域）
    source_connection_id: int = Field(..., alias="sourceConnectionId")
    source_database: str = Field(..., alias="sourceDatabase", min_length=1, max_length=256)
    source_schema: str | None = Field(default=None, alias="sourceSchema", max_length=256)
    # 工作连接（临时表/结果落库）
    work_connection_id: int = Field(..., alias="workConnectionId")
    work_database: str = Field(..., alias="workDatabase", min_length=1, max_length=256)
    work_schema: str | None = Field(default=None, alias="workSchema", max_length=256)

    model_config = {"populate_by_name": True}


class ProjectVO(BaseModel):
    id: int
    name: str
    description: str | None = None
    workspace_id: int = Field(alias="workspaceId")
    source_connection_id: int = Field(alias="sourceConnectionId")
    source_database: str | None = Field(default=None, alias="sourceDatabase")
    source_schema: str | None = Field(default=None, alias="sourceSchema")
    work_connection_id: int = Field(alias="workConnectionId")
    work_database: str | None = Field(default=None, alias="workDatabase")
    work_schema: str | None = Field(default=None, alias="workSchema")
    owner_user_id: int = Field(alias="ownerUserId")
    created_at: datetime | None = Field(default=None, alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class TreeWorkflowVO(BaseModel):
    id: int
    name: str
    kind: str = "workflow"


class TreeProjectVO(BaseModel):
    id: int
    name: str
    description: str | None = None
    source_connection_id: int = Field(alias="sourceConnectionId")
    source_database: str | None = Field(default=None, alias="sourceDatabase")
    source_schema: str | None = Field(default=None, alias="sourceSchema")
    work_connection_id: int = Field(alias="workConnectionId")
    work_database: str | None = Field(default=None, alias="workDatabase")
    work_schema: str | None = Field(default=None, alias="workSchema")
    workflows: list[TreeWorkflowVO] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SessionCreateRequest(BaseModel):
    project_id: int = Field(..., alias="projectId")
    title: str | None = None

    model_config = {"populate_by_name": True}


class ChatRequest(BaseModel):
    session_id: int = Field(..., alias="sessionId")
    message: str = Field(..., min_length=1)

    model_config = {"populate_by_name": True}


class WorkflowSaveRequest(BaseModel):
    project_id: int = Field(..., alias="projectId")
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    nodes_json: dict[str, Any] = Field(..., alias="nodesJson")
    draft_id: int | None = Field(default=None, alias="draftId")
    session_id: int | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}


class RunFeedbackRequest(BaseModel):
    """画布：有用 / 无用 / 保存记忆。"""

    action: str = Field(..., description="useful | useless | memory")
    session_id: int | None = Field(default=None, alias="sessionId")
    question: str | None = None

    model_config = {"populate_by_name": True}


class RunStartRequest(BaseModel):
    workflow_id: int = Field(..., alias="workflowId")
    session_id: int | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}


class ConfirmSqlCorrectRequest(BaseModel):
    """执行成功后用户确认 SQL 正确：写入样本 + 问句知识草稿。"""

    run_id: int = Field(..., alias="runId")
    session_id: int = Field(..., alias="sessionId")
    question: str | None = Field(default=None, description="用户原问句；空则取会话最近一条 user")
    hitl_resolution: dict[str, Any] | None = Field(default=None, alias="hitlResolution")

    model_config = {"populate_by_name": True}


class HitlResolveRequest(BaseModel):
    hitl_id: int = Field(..., alias="hitlId")
    resolution: dict[str, Any]

    model_config = {"populate_by_name": True}


# ---- 测评 ----


class EvalProjectCreateRequest(BaseModel):
    workspace_id: int = Field(..., alias="workspaceId")
    name: str = Field(..., min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=512)
    template_id: int = Field(..., alias="templateId")
    source_connection_id: int = Field(..., alias="sourceConnectionId")
    source_database: str = Field(..., alias="sourceDatabase", min_length=1, max_length=256)
    source_schema: str | None = Field(default=None, alias="sourceSchema", max_length=256)
    work_connection_id: int = Field(..., alias="workConnectionId")
    work_database: str = Field(..., alias="workDatabase", min_length=1, max_length=256)
    work_schema: str | None = Field(default=None, alias="workSchema", max_length=256)

    model_config = {"populate_by_name": True}


class EvalCaseCreateRequest(BaseModel):
    case_key: str | None = Field(default=None, alias="caseKey", max_length=64)
    category: str = Field(..., min_length=1, max_length=64)
    govern_subtype: str | None = Field(default=None, alias="governSubtype", max_length=32)
    question: str = Field(..., min_length=1)
    expect_sql: str | None = Field(default=None, alias="expectSql")
    compare_mode: str | None = Field(default=None, alias="compareMode", max_length=32)
    compare_spec: dict[str, Any] | None = Field(default=None, alias="compareSpec")
    hitl_replies: list[str] | None = Field(default=None, alias="hitlReplies")
    tags: list[str] | None = None
    difficulty: int | None = None

    model_config = {"populate_by_name": True}


class EvalCasePatchRequest(BaseModel):
    question: str | None = None
    expect_sql: str | None = Field(default=None, alias="expectSql")
    compare_mode: str | None = Field(default=None, alias="compareMode")
    compare_spec: dict[str, Any] | None = Field(default=None, alias="compareSpec")
    hitl_replies: list[str] | None = Field(default=None, alias="hitlReplies")
    govern_subtype: str | None = Field(default=None, alias="governSubtype")
    category: str | None = None
    tags: list[str] | None = None
    difficulty: int | None = None
    enabled: bool | None = None

    model_config = {"populate_by_name": True}


class EvalTaskCreateRequest(BaseModel):
    project_id: int = Field(..., alias="projectId")
    name: str | None = Field(default=None, max_length=128)
    case_ids: list[int] = Field(..., alias="caseIds", min_length=1)

    model_config = {"populate_by_name": True}


class EvalTaskPatchRequest(BaseModel):
    """测评任务可修改字段（当前仅名称）。"""

    name: str = Field(..., min_length=1, max_length=128)

    model_config = {"populate_by_name": True}


class EvalTaskStartRequest(BaseModel):
    """启动跑批 / 重新执行共用。

    taskCaseIds 非空：仅清理并执行这些任务用例快照；空/不传：清理全部后执行。
    已跑过的用例会清空历史结果后再跑。
    """

    task_case_ids: list[int] | None = Field(default=None, alias="taskCaseIds")

    model_config = {"populate_by_name": True}

