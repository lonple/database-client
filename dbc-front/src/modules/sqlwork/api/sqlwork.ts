import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { SQLWORK_BASE } from '@/modules/sqlwork/constants'

export interface WorkspaceSummary {
  id: number
  name: string
  description?: string | null
  spaceType?: string
  role?: string
}

export interface ConnectionSummary {
  connectionId: number
  name: string
  dbType: string
}

export interface AuthzTableRef {
  database?: string
  schema?: string
  name?: string
}

export interface AuthzGrantItem {
  mode: string
  connectionId?: number | null
  connectionName?: string | null
  dbType?: string | null
  scope?: string | null
  tables?: AuthzTableRef[]
  ops?: string[]
}

export interface MyWorkspaceAuthz {
  workspaceId: number
  workspaceName: string
  description?: string | null
  spaceType?: string
  role?: string
  spaceManager?: boolean
  grantAll?: boolean
  grants: AuthzGrantItem[]
}

export interface TableItem {
  schema?: string
  name: string
  objectType?: string
}

export interface TablePage {
  items: TableItem[]
  total: number
  page: number
  size: number
}

export interface StatementResult {
  index: number
  sqlPreview?: string
  statementType?: string
  columns: Array<{ name: string; type?: string }>
  rows: unknown[][]
  rowCount: number
  truncated: boolean
  elapsedMs: number
  affectedRows?: number | null
  success: boolean
  message?: string | null
  /** SUCCESS / WARN / ERROR */
  severity?: string | null
  globalPolicyAction?: string | null
  globalPolicyName?: string | null
  denyType?: string | null
  denyObjects?: string[] | null
  missingOps?: string[] | null
  grantedOps?: string[] | null
}

export interface ExecuteResult {
  totalCount: number
  successCount: number
  stoppedOnError: boolean
  message?: string | null
  elapsedMs: number
  sessionId?: string | null
  manualMode?: boolean
  inTransaction?: boolean
  statements: StatementResult[]
}

export interface WorkbenchSessionInfo {
  sessionId: string
  workspaceId: number
  connectionId: number
  database?: string | null
  schema?: string | null
  manualMode: boolean
  inTransaction: boolean
}

export function listMyWorkspaces() {
  return http.get(`${SQLWORK_BASE}/workspaces/mine`) as Promise<ApiResponse<WorkspaceSummary[]>>
}

export function listWorkspaceConnections(workspaceId: number) {
  return http.get(`${SQLWORK_BASE}/workspaces/${workspaceId}/connections`) as Promise<
    ApiResponse<ConnectionSummary[]>
  >
}

export function fetchMyAuthz(workspaceId: number) {
  return http.get(`${SQLWORK_BASE}/workspaces/${workspaceId}/my-authz`) as Promise<
    ApiResponse<MyWorkspaceAuthz>
  >
}

export function fetchDatabases(workspaceId: number, connectionId: number) {
  return http.get(`${SQLWORK_BASE}/meta/databases`, {
    params: { workspaceId, connectionId },
  }) as Promise<ApiResponse<string[]>>
}

export function fetchSchemas(workspaceId: number, connectionId: number, database?: string) {
  return http.get(`${SQLWORK_BASE}/meta/schemas`, {
    params: { workspaceId, connectionId, database },
  }) as Promise<ApiResponse<string[]>>
}

export function fetchTables(
  workspaceId: number,
  connectionId: number,
  params: { database?: string; schema?: string; keyword?: string; page?: number; size?: number },
) {
  return http.get(`${SQLWORK_BASE}/meta/tables`, {
    params: { workspaceId, connectionId, ...params },
  }) as Promise<ApiResponse<TablePage>>
}

export function createWorkbenchSession(data: {
  workspaceId: number
  connectionId: number
  database?: string
  schema?: string
  manualMode?: boolean
}) {
  return http.post(`${SQLWORK_BASE}/sessions`, data) as Promise<ApiResponse<WorkbenchSessionInfo>>
}

export function updateWorkbenchSession(
  sessionId: string,
  data: {
    connectionId?: number
    database?: string
    schema?: string
    manualMode?: boolean
  },
) {
  return http.put(`${SQLWORK_BASE}/sessions/${encodeURIComponent(sessionId)}`, data) as Promise<
    ApiResponse<WorkbenchSessionInfo>
  >
}

export function closeWorkbenchSession(sessionId: string) {
  return http.delete(`${SQLWORK_BASE}/sessions/${encodeURIComponent(sessionId)}`) as Promise<
    ApiResponse<null>
  >
}

export function executeSql(data: {
  workspaceId: number
  connectionId: number
  sql: string
  maxRows?: number
  database?: string
  schema?: string
  sessionId?: string
}) {
  return http.post(`${SQLWORK_BASE}/execute`, data, { timeout: 120000 }) as Promise<
    ApiResponse<ExecuteResult>
  >
}
