import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

/** 生成问数链路 TraceId（优先 crypto.randomUUID，去掉连字符对齐服务端 32 位 hex）。 */
export function newAskdataTraceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`.slice(0, 32)
}

function withTraceHeaders(extra?: Record<string, string>) {
  return {
    headers: {
      'X-Trace-Id': newAskdataTraceId(),
      ...(extra || {}),
    },
  }
}

export interface AskProject {
  id: number
  name: string
  description?: string | null
  workspaceId: number
  sourceConnectionId: number
  sourceDatabase?: string | null
  sourceSchema?: string | null
  workConnectionId: number
  workDatabase?: string | null
  workSchema?: string | null
  ownerUserId: number
  createdAt?: string
}

export interface TreeWorkflow {
  id: number
  name: string
  kind?: string
}

export interface TreeProject {
  id: number
  name: string
  description?: string | null
  sourceConnectionId: number
  sourceDatabase?: string | null
  sourceSchema?: string | null
  workConnectionId: number
  workDatabase?: string | null
  workSchema?: string | null
  workflows: TreeWorkflow[]
}

export interface HitlUiField {
  key: string
  label: string
  required?: boolean
  candidates?: string[]
}

export interface HitlUi {
  kind?: string
  title?: string
  hint?: string
  fields?: HitlUiField[]
}

export interface ChatResponse {
  reply: string
  draftId?: number | null
  hitlId?: number | null
  draft?: {
    name?: string
    nodes?: Array<{ id: string; type: string; title?: string; sql?: string; readonly?: boolean }>
  } | null
  needsHitl?: boolean
  route?: string
  traceId?: string
  turnId?: number | null
  hitlUi?: HitlUi | null
}

export interface RunFeedbackState {
  runId?: number
  workflowId?: number
  usefulDone?: boolean
  uselessDone?: boolean
  memoryDone?: boolean
  sampleId?: number | null
  knowledgeSaved?: boolean
}

export interface RunDetail {
  id: number
  status: string
  errorMessage?: string | null
  sessionId?: number | null
  workflowId?: number | null
  startedAt?: string | null
  finishedAt?: string | null
  /** 工作流执行墙钟耗时（finishedAt - startedAt） */
  elapsedMs?: number | null
  feedbackReady?: boolean
  feedback?: RunFeedbackState | null
  logs: Array<{ id: number; level: string; message: string; createdAt?: string }>
  result?: {
    columns?: Array<{ name: string; type?: string }>
    rows?: unknown[][]
    rowCount?: number
    truncated?: boolean
  } | null
}

export interface LlmSpanItem {
  id: number
  traceId?: string
  turnId?: number
  phase: string
  kind: string
  name: string
  status: string
  latencyMs?: number
  tokenIn?: number | null
  tokenOut?: number | null
  model?: string
  residency?: string
  workspaceId?: number
  projectId?: number
  errorMessage?: string
  startedAt?: string
  finishedAt?: string
}

export interface AskTurnItem {
  id: number
  rootTraceId?: string
  question: string
  status: string
  workspaceId?: number
  projectId?: number
  sessionId?: number
  userId?: number
  hitlId?: number
  route?: string
  tokenIn?: number
  tokenOut?: number
  tokenTotal?: number
  spanCount?: number
  latencyMs?: number | null
  errorMessage?: string
  startedAt?: string
  finishedAt?: string
}

export function fetchProjects(workspaceId: number) {
  return http.get(`${ASKDATA_BASE}/api/projects`, {
    params: { workspace_id: workspaceId },
  }) as Promise<ApiResponse<AskProject[]>>
}

export function createProject(body: {
  workspaceId: number
  name: string
  description?: string
  sourceConnectionId: number
  sourceDatabase: string
  sourceSchema?: string
  workConnectionId: number
  workDatabase: string
  workSchema?: string
}) {
  return http.post(`${ASKDATA_BASE}/api/projects`, body) as Promise<ApiResponse<AskProject>>
}

export function fetchTree(workspaceId: number) {
  return http.get(`${ASKDATA_BASE}/api/tree`, {
    params: { workspace_id: workspaceId },
  }) as Promise<ApiResponse<TreeProject[]>>
}

export function createSession(projectId: number, title?: string) {
  return http.post(`${ASKDATA_BASE}/api/sessions`, { projectId, title }) as Promise<
    ApiResponse<{ id: number; projectId: number; title?: string }>
  >
}

export interface SessionMessage {
  id: number
  role: string
  content: string
  contentType?: string
  payload?: {
    draftId?: number | null
    hitlId?: number | null
    draft?: ChatResponse['draft']
    route?: string
    traceId?: string
    turnId?: number | null
    saved?: boolean
    workflowId?: number | null
  } | null
  createdAt?: string
}

export function openSession(projectId: number, title?: string) {
  return http.post(`${ASKDATA_BASE}/api/sessions/open`, { projectId, title }) as Promise<
    ApiResponse<{
      id: number
      projectId: number
      title?: string
      created?: boolean
      pendingHitlId?: number | null
      pendingHitlQuestion?: string | null
      messages: SessionMessage[]
    }>
  >
}

export function fetchSessionMessages(sessionId: number) {
  return http.get(`${ASKDATA_BASE}/api/sessions/${sessionId}/messages`) as Promise<
    ApiResponse<SessionMessage[]>
  >
}

export function clearSessionMessages(sessionId: number) {
  return http.delete(`${ASKDATA_BASE}/api/sessions/${sessionId}/messages`) as Promise<
    ApiResponse<{ sessionId: number; deletedMessages: number; deletedPendingHitl: number }>
  >
}

export function fetchWorkLogs(sessionId: number, after = 0, turnId?: number | null) {
  return http.get(`${ASKDATA_BASE}/api/sessions/${sessionId}/work-logs`, {
    params: {
      after,
      ...(turnId != null ? { turnId } : {}),
    },
    timeout: 10000,
  }) as Promise<
    ApiResponse<{
      total: number
      items: Array<{ id?: number; at: string; level: string; message: string }>
      next: number
      turnId?: number | null
    }>
  >
}

export function fetchSessionLlmSpans(sessionId: number) {
  return http.get(`${ASKDATA_BASE}/api/sessions/${sessionId}/llm-spans`) as Promise<
    ApiResponse<{
      sessionId: number
      items: Array<{
        id: number
        phase?: string
        kind?: string
        name?: string
        status?: string
        latencyMs?: number
        model?: string
        errorMessage?: string
        startedAt?: string
        finishedAt?: string
      }>
    }>
  >
}

export function chat(sessionId: number, message: string) {
  return http.post(`${ASKDATA_BASE}/api/chat`, { sessionId, message }, {
    timeout: 300000,
    ...withTraceHeaders(),
  }) as Promise<ApiResponse<ChatResponse>>
}

/** 工作台今日 LLM 额度；测评页不要调用 */
export function fetchQuotaMe() {
  return http.get(`${ASKDATA_BASE}/api/quota/me`, {
    ...withTraceHeaders(),
  }) as Promise<
    ApiResponse<{
      usageDate: string
      used: number
      limit: number
      remaining: number | null
      enabled: boolean
    }>
  >
}

export function saveWorkflow(body: {
  projectId: number
  name: string
  description?: string
  nodesJson: Record<string, unknown>
  draftId?: number
  sessionId?: number
}) {
  return http.post(`${ASKDATA_BASE}/api/workflows`, body) as Promise<
    ApiResponse<{
      id: number
      name: string
      projectId: number
      alreadySaved?: boolean
      messageId?: number | null
    }>
  >
}

export function fetchWorkflow(workflowId: number) {
  return http.get(`${ASKDATA_BASE}/api/workflows/${workflowId}`) as Promise<
    ApiResponse<{ id: number; name: string; projectId: number; nodesJson: Record<string, unknown> }>
  >
}

export function deleteProject(projectId: number) {
  return http.delete(`${ASKDATA_BASE}/api/projects/${projectId}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function deleteWorkflow(workflowId: number) {
  return http.delete(`${ASKDATA_BASE}/api/workflows/${workflowId}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function startRun(workflowId: number, sessionId?: number) {
  return http.post(
    `${ASKDATA_BASE}/api/runs`,
    { workflowId, sessionId },
    { timeout: 300000, ...withTraceHeaders() },
  ) as Promise<ApiResponse<{ id: number; status: string; errorMessage?: string; traceId?: string }>>
}

/** 执行成功后确认 SQL 正确：写入样本 + 问句知识草稿（待审批） */
export function confirmSqlCorrect(body: {
  runId: number
  sessionId: number
  question?: string
  hitlResolution?: Record<string, unknown>
}) {
  return http.post(`${ASKDATA_BASE}/api/runs/confirm-correct`, body, {
    ...withTraceHeaders(),
  }) as Promise<
    ApiResponse<{
      sampleId: number
      workflowId: number
      runId: number
      question: string
      knowledge?: Record<string, unknown>
    }>
  >
}

/** 画布：有用 / 无用 / 保存记忆（幂等） */
export function submitRunFeedback(
  runId: number,
  body: { action: 'useful' | 'useless' | 'memory'; sessionId?: number; question?: string },
) {
  return http.post(`${ASKDATA_BASE}/api/runs/${runId}/feedback`, body, {
    ...withTraceHeaders(),
  }) as Promise<
    ApiResponse<{
      alreadyProcessed?: boolean
      action?: string
      message?: string
      sampleId?: number
      knowledge?: Record<string, unknown>
      feedback?: RunFeedbackState
    }>
  >
}

export function stopRun(runId: number) {
  return http.post(`${ASKDATA_BASE}/api/runs/${runId}/stop`) as Promise<
    ApiResponse<{ id: number; status: string }>
  >
}

export function fetchRun(runId: number) {
  return http.get(`${ASKDATA_BASE}/api/runs/${runId}`) as Promise<ApiResponse<RunDetail>>
}

export function resolveHitl(hitlId: number, resolution: Record<string, unknown>) {
  return http.post(
    `${ASKDATA_BASE}/api/hitl/resolve`,
    { hitlId, resolution },
    { timeout: 300000, ...withTraceHeaders() },
  ) as Promise<
    ApiResponse<{
      id: number
      status: string
      reply?: string
      draftId?: number
      draft?: ChatResponse['draft']
      needsHitl?: boolean
      traceId?: string
    }>
  >
}

export function fetchAskTurns(params: {
  page: number
  size: number
  workspaceId?: number
  projectId?: number
  status?: string
}) {
  return http.get(`${ASKDATA_BASE}/api/admin/llm/turns`, {
    params: {
      page: params.page,
      size: params.size,
      workspace_id: params.workspaceId,
      project_id: params.projectId,
      status: params.status,
    },
  }) as Promise<ApiResponse<{ page: number; size: number; total: number; items: AskTurnItem[] }>>
}

export function fetchLlmSpans(params: {
  page: number
  size: number
  workspaceId?: number
  kind?: string
  status?: string
  turnId?: number
  traceId?: string
}) {
  return http.get(`${ASKDATA_BASE}/api/admin/llm/spans`, {
    params: {
      page: params.page,
      size: params.size,
      workspace_id: params.workspaceId,
      kind: params.kind,
      status: params.status,
      turn_id: params.turnId,
      trace_id: params.traceId,
    },
  }) as Promise<ApiResponse<{ page: number; size: number; total: number; items: LlmSpanItem[] }>>
}

export function fetchLlmSummary(hours = 24) {
  return http.get(`${ASKDATA_BASE}/api/admin/llm/summary`, {
    params: { hours },
  }) as Promise<
    ApiResponse<{
      hours: number
      buckets: Array<{ kind: string; status: string; count: number; avgLatencyMs: number }>
    }>
  >
}

export function fetchSpanDetail(id: number) {
  return http.get(`${ASKDATA_BASE}/api/admin/llm/spans/${id}`) as Promise<ApiResponse<Record<string, unknown>>>
}
