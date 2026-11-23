import http from '@/common/api/http'

const BASE = '/dbc-graph'

export interface GraphRow {
  id: number
  categoryId?: number
  code: string
  name: string
  summary: string
  productName?: string
  updatedAt?: string
}

export interface GraphNode {
  nodeId: string
  name: string
  nodeType?: string
  description?: string
  gender?: string
  props?: Record<string, unknown>
  x: number
  y: number
}

export interface GraphEdge {
  edgeId: string
  fromNodeId: string
  toNodeId: string
  relType: string
  description?: string
}

export interface CanvasData {
  graphId: number
  name: string
  summary: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

type Envelope<T> = { code: number; message: string; data: T }

function data<T>(resp: Envelope<T> | T): T {
  if (resp && typeof resp === 'object' && 'data' in (resp as Envelope<T>) && 'code' in (resp as Envelope<T>)) {
    return (resp as Envelope<T>).data
  }
  return resp as T
}

export interface TableRelationImportResult {
  graph: GraphRow
  tableCount: number
  fkCount: number
  nodeCount: number
  edgeCount: number
  replaced: boolean
}

export const graphApi = {
  async list(keyword?: string) {
    const resp = (await http.get(`${BASE}/api/graphs`, { params: { keyword } })) as Envelope<GraphRow[]>
    return data(resp) || []
  },
  async create(body: { code: string; name: string; summary: string; productName?: string }) {
    const resp = (await http.post(`${BASE}/api/graphs`, body)) as Envelope<GraphRow>
    return data(resp)
  },
  async importMd(body: {
    markdown: string
    code?: string
    name?: string
    summary?: string
    productName?: string
    force?: boolean
  }) {
    const resp = (await http.post(`${BASE}/api/graphs/import-md`, body, {
      timeout: 180000,
    })) as Envelope<TableRelationImportResult>
    return data(resp)
  },
  async update(id: number, body: Partial<{ code: string; name: string; summary: string; productName: string }>) {
    const resp = (await http.patch(`${BASE}/api/graphs/${id}`, body)) as Envelope<GraphRow>
    return data(resp)
  },
  async remove(id: number) {
    await http.delete(`${BASE}/api/graphs/${id}`)
  },
  async getCanvas(id: number) {
    const resp = (await http.get(`${BASE}/api/graphs/${id}/canvas`)) as Envelope<CanvasData>
    return data(resp)
  },
  async createNode(graphId: number, body: Partial<GraphNode> & { name?: string }) {
    const resp = (await http.post(`${BASE}/api/graphs/${graphId}/nodes`, body)) as Envelope<GraphNode>
    return data(resp)
  },
  async updateNode(graphId: number, nodeId: string, body: Partial<GraphNode>) {
    const resp = (await http.patch(`${BASE}/api/graphs/${graphId}/nodes/${nodeId}`, body)) as Envelope<GraphNode>
    return data(resp)
  },
  async updatePosition(graphId: number, nodeId: string, x: number, y: number) {
    await http.patch(`${BASE}/api/graphs/${graphId}/nodes/${nodeId}/position`, { x, y })
  },
  async deleteNode(graphId: number, nodeId: string) {
    await http.delete(`${BASE}/api/graphs/${graphId}/nodes/${nodeId}`)
  },
  async createEdge(graphId: number, body: { fromNodeId: string; toNodeId: string; relType: string; description?: string }) {
    const resp = (await http.post(`${BASE}/api/graphs/${graphId}/edges`, body)) as Envelope<GraphEdge>
    return data(resp)
  },
  async updateEdge(graphId: number, edgeId: string, body: { relType?: string; description?: string }) {
    const resp = (await http.patch(`${BASE}/api/graphs/${graphId}/edges/${edgeId}`, body)) as Envelope<GraphEdge>
    return data(resp)
  },
  async deleteEdge(graphId: number, edgeId: string) {
    await http.delete(`${BASE}/api/graphs/${graphId}/edges/${edgeId}`)
  },
}
