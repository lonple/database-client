import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

export interface AskDocumentRow {
  id: number
  name: string
  sourceFormat: string
  sourceFilename?: string
  pipeline: string
  convertStatus: string
  convertError?: string | null
  markdown?: string | null
  markdownEdited?: boolean
  knowledgeDocumentId?: number | null
  createdAt?: string
  updatedAt?: string
}

export function listAskDocuments(params?: {
  q?: string
  sourceFormat?: string
  convertStatus?: string
}) {
  return http.get(`${ASKDATA_BASE}/api/documents`, { params }) as Promise<
    ApiResponse<AskDocumentRow[]>
  >
}

export function getAskDocument(id: number) {
  return http.get(`${ASKDATA_BASE}/api/documents/${id}`) as Promise<ApiResponse<AskDocumentRow>>
}

export function uploadAskDocument(file: File, name?: string) {
  const fd = new FormData()
  fd.append('file', file)
  if (name) fd.append('name', name)
  return http.post(`${ASKDATA_BASE}/api/documents`, fd, { timeout: 180000 }) as Promise<
    ApiResponse<AskDocumentRow>
  >
}

export function patchAskDocument(id: number, body: { name?: string; markdown?: string }) {
  return http.patch(`${ASKDATA_BASE}/api/documents/${id}`, body) as Promise<
    ApiResponse<AskDocumentRow>
  >
}

export function replaceAskDocument(id: number, file: File, confirmOverwrite: boolean) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('confirmOverwrite', confirmOverwrite ? 'true' : 'false')
  return http.post(`${ASKDATA_BASE}/api/documents/${id}/replace`, fd, {
    timeout: 180000,
  }) as Promise<ApiResponse<AskDocumentRow>>
}

export function retryAskDocument(id: number) {
  return http.post(`${ASKDATA_BASE}/api/documents/${id}/retry`) as Promise<
    ApiResponse<AskDocumentRow>
  >
}

export function deleteAskDocument(id: number) {
  return http.delete(`${ASKDATA_BASE}/api/documents/${id}`) as Promise<
    ApiResponse<{ id: number; deleted: boolean }>
  >
}

export function downloadAskDocumentSourceUrl(id: number) {
  return `${ASKDATA_BASE}/api/documents/${id}/source`
}
