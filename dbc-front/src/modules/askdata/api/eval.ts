import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

export interface EvalTemplate {
  id: number
  code: string
  name: string
  version: string
  remark?: string | null
  enabled: boolean
}

export interface EvalProject {
  id: number
  workspaceId: number
  name: string
  remark?: string | null
  templateId: number
  sourceConnectionId: number
  sourceDatabase?: string | null
  sourceSchema?: string | null
  workConnectionId: number
  workDatabase?: string | null
  workSchema?: string | null
  askProjectId: number
  ownerUserId: number
  createdAt?: string
}

export interface EvalCase {
  id: number
  caseKey: string
  scope: string
  templateId?: number | null
  projectId?: number | null
  category: string
  governSubtype?: string | null
  question: string
  expectSql?: string | null
  compareMode: string
  compareSpec?: Record<string, unknown>
  hitlReplies?: string[] | null
  tags?: string[] | null
  difficulty?: number | null
  enabled: boolean
}

export interface EvalCategoryMetric {
  category: string
  total: number
  passed: number
  exactPass: number
  refuseOk: number
  askFailed: number
  passRate?: number | null
  tableSelectOk?: number
  tableSelectScored?: number
  tableSelectRate?: number | null
}

export interface EvalTaskMetrics {
  total?: number
  passed?: number
  passRate?: number | null
  exactPass?: number
  partialGe80?: number
  askFailed?: number
  hasResult?: number
  hitlSupplementPass?: number
  refuseOk?: number
  refuseBadLeak?: number
  boardPass?: number
  tableSelectOk?: number
  tableSelectScored?: number
  tableSelectRate?: number | null
  elapsedMs?: number
  elapsedMsSum?: number
  elapsedMsAvg?: number
  elapsedCaseCount?: number
  byCategory?: EvalCategoryMetric[]
}

export interface EvalTask {
  id: number
  projectId: number
  workspaceId: number
  name: string
  status: string
  metrics?: EvalTaskMetrics | null
  errorMessage?: string | null
  createdBy: number
  startedAt?: string | null
  finishedAt?: string | null
  createdAt?: string
  elapsedMs?: number | null
}

export interface EvalTaskCase {
  id: number
  taskId: number
  caseId?: number | null
  caseKey: string
  question: string
  expectSql?: string | null
  compareMode: string
  compareSpec?: Record<string, unknown>
  governSubtype?: string | null
  hitlReplies?: string[] | null
  status: string
  askSql?: string | null
  askError?: string | null
  hitlRounds: number
  compareScore?: number | null
  compareDetail?: Record<string, unknown> | null
  expectRowCount?: number | null
  askRowCount?: number | null
  traceId?: string | null
  workflowId?: number | null
  runId?: number | null
  sessionId?: number | null
  startedAt?: string | null
  finishedAt?: string | null
  elapsedMs?: number | null
}

export function listEvalTemplates() {
  return http.get(`${ASKDATA_BASE}/api/eval/templates`) as Promise<ApiResponse<EvalTemplate[]>>
}

export function listEvalProjects(workspaceId: number) {
  return http.get(`${ASKDATA_BASE}/api/eval/projects`, {
    params: { workspaceId },
  }) as Promise<ApiResponse<EvalProject[]>>
}

export function createEvalProject(body: {
  workspaceId: number
  name: string
  remark?: string
  templateId: number
  sourceConnectionId: number
  sourceDatabase: string
  sourceSchema?: string
  workConnectionId: number
  workDatabase: string
  workSchema?: string
}) {
  return http.post(`${ASKDATA_BASE}/api/eval/projects`, body) as Promise<ApiResponse<EvalProject>>
}

export function deleteEvalProject(projectId: number) {
  return http.delete(`${ASKDATA_BASE}/api/eval/projects/${projectId}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function listEvalCases(
  projectId: number,
  params?: { category?: string; page?: number; pageSize?: number },
) {
  return http.get(`${ASKDATA_BASE}/api/eval/projects/${projectId}/cases`, {
    params: {
      category: params?.category,
      page: params?.page ?? 1,
      pageSize: params?.pageSize ?? 50,
    },
  }) as Promise<
    ApiResponse<{ items: EvalCase[]; page: number; pageSize: number; total: number }>
  >
}

export function createEvalCase(
  projectId: number,
  body: {
    caseKey?: string
    category: string
    governSubtype?: string
    question: string
    expectSql?: string
    compareMode?: string
    compareSpec?: Record<string, unknown>
    hitlReplies?: string[]
    tags?: string[]
  },
) {
  return http.post(`${ASKDATA_BASE}/api/eval/projects/${projectId}/cases`, body) as Promise<
    ApiResponse<EvalCase>
  >
}

export function deleteEvalCase(caseId: number) {
  return http.delete(`${ASKDATA_BASE}/api/eval/cases/${caseId}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function createEvalTask(body: { projectId: number; name?: string; caseIds: number[] }) {
  return http.post(`${ASKDATA_BASE}/api/eval/tasks`, body) as Promise<ApiResponse<EvalTask>>
}

export function patchEvalTask(taskId: number, body: { name: string }) {
  return http.patch(`${ASKDATA_BASE}/api/eval/tasks/${taskId}`, body) as Promise<ApiResponse<EvalTask>>
}

export function startEvalTask(taskId: number, body?: { taskCaseIds?: number[] }) {
  // 启动前可能需等待上一轮后台收尾，超时放宽
  return http.post(
    `${ASKDATA_BASE}/api/eval/tasks/${taskId}/start`,
    body?.taskCaseIds?.length ? { taskCaseIds: body.taskCaseIds } : {},
    { timeout: 180_000 },
  ) as Promise<ApiResponse<EvalTask>>
}

export function cancelEvalTask(taskId: number) {
  return http.post(`${ASKDATA_BASE}/api/eval/tasks/${taskId}/cancel`) as Promise<ApiResponse<EvalTask>>
}

export function deleteEvalTask(taskId: number) {
  return http.delete(`${ASKDATA_BASE}/api/eval/tasks/${taskId}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function listEvalTasks(params: { workspaceId?: number; projectId?: number }) {
  return http.get(`${ASKDATA_BASE}/api/eval/tasks`, {
    params: {
      workspaceId: params.workspaceId,
      projectId: params.projectId,
    },
  }) as Promise<ApiResponse<EvalTask[]>>
}

export function getEvalTask(taskId: number) {
  return http.get(`${ASKDATA_BASE}/api/eval/tasks/${taskId}`) as Promise<ApiResponse<EvalTask>>
}

export function listEvalTaskCases(
  taskId: number,
  params?: { page?: number; pageSize?: number; status?: string; category?: string },
) {
  return http.get(`${ASKDATA_BASE}/api/eval/tasks/${taskId}/cases`, {
    params: {
      page: params?.page ?? 1,
      pageSize: params?.pageSize ?? 50,
      status: params?.status,
      category: params?.category,
    },
  }) as Promise<
    ApiResponse<{
      items: EvalTaskCase[]
      page: number
      pageSize: number
      total: number
      task: EvalTask
    }>
  >
}
