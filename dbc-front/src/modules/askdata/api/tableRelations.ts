import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

export interface TableRelationBinding {
  id: number
  name: string
  workspaceId?: number | null
  connectionId: number
  connectionName?: string | null
  database?: string | null
  schema?: string | null
  graphId: number
  graphName?: string | null
  remark?: string | null
  ownerUserId?: number
  createdAt?: string
  updatedAt?: string
}

export interface AdaGraphOption {
  id: number
  name: string
  summary?: string
  productName?: string
  categoryId?: number
}

export function listTableRelationBindings(params?: { q?: string; connectionId?: number }) {
  return http.get(`${ASKDATA_BASE}/api/table-relation-bindings`, { params }) as Promise<
    ApiResponse<TableRelationBinding[]>
  >
}

export function createTableRelationBinding(body: {
  name: string
  workspaceId?: number
  connectionId: number
  connectionName?: string
  database?: string
  schema?: string
  graphId: number
  graphName?: string
  remark?: string
}) {
  return http.post(`${ASKDATA_BASE}/api/table-relation-bindings`, body) as Promise<
    ApiResponse<TableRelationBinding>
  >
}

export function updateTableRelationBinding(
  id: number,
  body: Partial<{
    name: string
    workspaceId: number
    connectionId: number
    connectionName: string
    database: string
    schema: string
    graphId: number
    graphName: string
    remark: string
  }>,
) {
  return http.patch(`${ASKDATA_BASE}/api/table-relation-bindings/${id}`, body) as Promise<
    ApiResponse<TableRelationBinding>
  >
}

export function deleteTableRelationBinding(id: number) {
  return http.delete(`${ASKDATA_BASE}/api/table-relation-bindings/${id}`) as Promise<
    ApiResponse<null>
  >
}

export function listAdaGraphs(params?: { keyword?: string; productName?: string }) {
  return http.get(`${ASKDATA_BASE}/api/table-relation-bindings/graphs`, { params }) as Promise<
    ApiResponse<AdaGraphOption[]>
  >
}
