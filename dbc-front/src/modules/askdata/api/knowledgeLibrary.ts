import http from '@/common/api/http'

const BASE = '/dbc-knowledge'

export interface CategoryNode {
  id: number
  parentId?: number | null
  name: string
  code: string
  children?: CategoryNode[]
}

export interface DocumentRow {
  id: number
  title: string
  summary?: string
  status: string
  categoryId?: number
  sliceCount?: number
  vectorSyncStatus?: string
  productName?: string
  updatedAt?: string
}

export interface SliceRow {
  id?: number
  seqNo?: number
  title: string
  description?: string
  bodySummary?: string
  body?: string
  orientation?: string
  status?: string
}

type Envelope<T> = { code: number; message: string; data: T }

function unwrap<T>(resp: Envelope<T> | T): T {
  if (resp && typeof resp === 'object' && 'code' in (resp as Envelope<T>) && 'data' in (resp as Envelope<T>)) {
    return (resp as Envelope<T>).data
  }
  return resp as T
}

export const knowledgeLibraryApi = {
  async tree() {
    const resp = (await http.get(`${BASE}/api/categories/tree`)) as Envelope<CategoryNode[]>
    return unwrap(resp) || []
  },
  async createCategory(body: { name: string; code: string; parentId?: number | null }) {
    const resp = (await http.post(`${BASE}/api/categories`, body)) as Envelope<CategoryNode>
    return unwrap(resp)
  },
  async renameCategory(id: number, name: string) {
    const resp = (await http.patch(`${BASE}/api/categories/${id}`, { name })) as Envelope<CategoryNode>
    return unwrap(resp)
  },
  async removeCategory(id: number) {
    await http.delete(`${BASE}/api/categories/${id}`)
  },
  async listDocuments(categoryId?: number) {
    const resp = (await http.get(`${BASE}/api/documents`, {
      params: { categoryId },
    })) as Envelope<DocumentRow[]>
    return unwrap(resp) || []
  },
  async detail(id: number) {
    const resp = (await http.get(`${BASE}/api/documents/${id}`)) as Envelope<
      DocumentRow & { body?: string; summary?: string; slices?: SliceRow[] }
    >
    return unwrap(resp)
  },
  async createDocument(body: {
    title: string
    summary: string
    body: string
    categoryId: number
    productName?: string
    orientation?: string
  }) {
    const resp = (await http.post(`${BASE}/api/documents`, {
      orientation: 'BOTH',
      productName: 'dbc产品',
      sourceType: 'MANUAL',
      ...body,
    })) as Envelope<DocumentRow>
    return unwrap(resp)
  },
  async updateDocument(id: number, body: { title?: string; summary?: string; body?: string; categoryId?: number }) {
    const resp = (await http.put(`${BASE}/api/documents/${id}`, body)) as Envelope<DocumentRow>
    return unwrap(resp)
  },
  async remove(id: number) {
    await http.delete(`${BASE}/api/documents/${id}`)
  },
  async suggestSlices(id: number) {
    const resp = (await http.post(
      `${BASE}/api/documents/${id}/suggest-slices?force=true`,
      {},
      { timeout: 180000 },
    )) as Envelope<SliceRow[]>
    return unwrap(resp) || []
  },
  async saveSlices(id: number, slices: SliceRow[]) {
    const resp = (await http.put(`${BASE}/api/documents/${id}/slices`, { slices })) as Envelope<SliceRow[]>
    return unwrap(resp) || []
  },
  async publish(id: number) {
    const resp = (await http.post(`${BASE}/api/documents/${id}/publish`, {}, { timeout: 180000 })) as Envelope<unknown>
    return unwrap(resp)
  },
  async unpublish(id: number) {
    const resp = (await http.post(`${BASE}/api/documents/${id}/unpublish`)) as Envelope<unknown>
    return unwrap(resp)
  },
}
