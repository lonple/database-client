import http from '@/common/api/http'
import type { ApiResponse, PageResult } from '@/common/api/types'
import { AUDIT_BASE } from '@/modules/audit/constants'

export interface SqlAuditLog {
  eventId: string
  category: string
  batchId?: string
  statementIndex?: number
  operatorUserId?: number
  operatorUsername?: string
  clientIp?: string
  workspaceId?: number
  workspaceName?: string
  connectionId?: number
  connectionName?: string
  dbType?: string
  occurredAt?: string
  status?: string
  statementType?: string
  sqlText?: string
  sqlTruncated?: boolean
  elapsedMs?: number
  failDetail?: Record<string, unknown>
}

export interface BizAuditLog {
  eventId: string
  category: string
  module?: string
  action?: string
  resourceType?: string
  resourceId?: string
  operatorUserId?: number
  operatorUsername?: string
  clientIp?: string
  occurredAt?: string
  result?: string
  failReason?: string
  details?: Record<string, unknown>
}

export function fetchSqlLogs(params: {
  page: number
  size: number
  from?: string
  to?: string
  operatorUsername?: string
  workspaceId?: number
  connectionId?: number
  status?: string
  sqlKeyword?: string
}) {
  return http.get(`${AUDIT_BASE}/sql-logs`, { params }) as Promise<ApiResponse<PageResult<SqlAuditLog>>>
}

export function fetchSqlLogDetail(eventId: string) {
  return http.get(`${AUDIT_BASE}/sql-logs/${eventId}`) as Promise<ApiResponse<SqlAuditLog>>
}

export function fetchBizLogs(params: {
  page: number
  size: number
  from?: string
  to?: string
  operatorUsername?: string
  module?: string
  action?: string
  result?: string
  keyword?: string
}) {
  return http.get(`${AUDIT_BASE}/biz-logs`, { params }) as Promise<ApiResponse<PageResult<BizAuditLog>>>
}

export function fetchBizLogDetail(eventId: string) {
  return http.get(`${AUDIT_BASE}/biz-logs/${eventId}`) as Promise<ApiResponse<BizAuditLog>>
}
