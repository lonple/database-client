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

    model_config = {"populate_by_name": True}


class RunStartRequest(BaseModel):
    workflow_id: int = Field(..., alias="workflowId")
    session_id: int | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}


class HitlResolveRequest(BaseModel):
    hitl_id: int = Field(..., alias="hitlId")
    resolution: dict[str, Any]

    model_config = {"populate_by_name": True}
