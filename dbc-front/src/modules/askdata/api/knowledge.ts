import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

export type KnowledgeCategory = 'GENERAL' | 'METADATA' | 'QUESTION'

export interface KnowledgeBinding {
  id: number
  name: string
  workspaceId?: number | null
  connectionId: number
  connectionName?: string | null
  database?: string | null
  schema?: string | null
  documentId: number
  documentName?: string | null
  knowledgeCategory: KnowledgeCategory
  remark?: string | null
  ownerUserId?: number
  createdAt?: string
  updatedAt?: string
}

export interface AdaKnowledgeDocumentOption {
  id: number
  title: string
  summary?: string
  productName?: string
  status?: string
  sourceType?: string
}

export function listKnowledgeBindings(params?: {
  q?: string
  connectionId?: number
  knowledgeCategory?: KnowledgeCategory
}) {
  return http.get(`${ASKDATA_BASE}/api/knowledge-bindings`, { params }) as Promise<
    ApiResponse<KnowledgeBinding[]>
  >
}

export function createKnowledgeBinding(body: {
  name: string
  workspaceId?: number
  connectionId: number
  connectionName?: string
  database?: string
  schema?: string
  documentId: number
  documentName?: string
  knowledgeCategory: KnowledgeCategory
  remark?: string
}) {
  return http.post(`${ASKDATA_BASE}/api/knowledge-bindings`, body) as Promise<
    ApiResponse<KnowledgeBinding>
  >
}

export function updateKnowledgeBinding(
  id: number,
  body: Partial<{
    name: string
    workspaceId: number
    connectionId: number
    connectionName: string
    database: string
    schema: string
    documentId: number
    documentName: string
    knowledgeCategory: KnowledgeCategory
    remark: string
  }>,
) {
  return http.patch(`${ASKDATA_BASE}/api/knowledge-bindings/${id}`, body) as Promise<
    ApiResponse<KnowledgeBinding>
  >
}

export function deleteKnowledgeBinding(id: number) {
  return http.delete(`${ASKDATA_BASE}/api/knowledge-bindings/${id}`) as Promise<
    ApiResponse<null>
  >
}

export function listAdaKnowledgeDocuments(params?: { status?: string }) {
  return http.get(`${ASKDATA_BASE}/api/knowledge-bindings/documents`, {
    params,
  }) as Promise<ApiResponse<AdaKnowledgeDocumentOption[]>>
}
