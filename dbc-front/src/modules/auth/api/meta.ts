import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { MANAGE_BASE } from '@/modules/manage/constants'

export interface MetaTableItem {
  schema?: string
  name: string
  objectType?: string
}

export interface MetaTablePage {
  items: MetaTableItem[]
  total: number
  page: number
  size: number
}

/** 工作空间授权选表：经 manage 代理 sqlwork /inner/meta（不做成员表过滤） */
export function fetchDatabases(workspaceId: number, connectionId: number) {
  return http.get(`${MANAGE_BASE}/workspaces/${workspaceId}/meta/databases`, {
    params: { connectionId },
  }) as Promise<ApiResponse<string[]>>
}

export function fetchSchemas(workspaceId: number, connectionId: number, database?: string) {
  return http.get(`${MANAGE_BASE}/workspaces/${workspaceId}/meta/schemas`, {
    params: { connectionId, database },
  }) as Promise<ApiResponse<string[]>>
}

export function fetchTables(
  workspaceId: number,
  connectionId: number,
  params: { database?: string; schema?: string; keyword?: string; page?: number; size?: number },
) {
  return http.get(`${MANAGE_BASE}/workspaces/${workspaceId}/meta/tables`, {
    params: { connectionId, ...params },
  }) as Promise<ApiResponse<MetaTablePage>>
}
