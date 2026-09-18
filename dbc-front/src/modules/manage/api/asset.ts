import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { MANAGE_BASE } from '@/modules/manage/constants'

export interface InstanceView {
  id: number
  name: string
  deptId?: number | null
  ownerScope?: string
  ownerUserId?: number | null
  dbType: string
  host: string
  port: number
  driverFileName?: string | null
  driverStoragePath?: string | null
  driverSha256?: string | null
  driverSize?: number | null
  driverClassName?: string | null
  status: number
  description?: string | null
  createdAt?: string
  updatedAt?: string
}

export interface ConnectionView {
  id: number
  name: string
  deptId?: number | null
  ownerScope?: string
  ownerUserId?: number | null
  instanceId: number
  instanceName?: string
  dbType: string
  username: string
  passwordMasked?: string
  initialDatabase?: string | null
  status: number
  createdAt?: string
  updatedAt?: string
}

export interface DeptTreeNode {
  id: number
  name: string
  description?: string | null
  parentId?: number | null
  level: number
  path: string
  children?: DeptTreeNode[]
}

export function listDeptTree() {
  return http.get(`${MANAGE_BASE}/depts/tree`) as Promise<ApiResponse<DeptTreeNode[]>>
}

export function listInstances() {
  return http.get(`${MANAGE_BASE}/instances`) as Promise<ApiResponse<InstanceView[]>>
}

export function listSelectableInstances(dbType?: string) {
  return http.get(`${MANAGE_BASE}/instances/selectable`, {
    params: dbType ? { dbType } : undefined,
  }) as Promise<ApiResponse<InstanceView[]>>
}

export function createInstance(data: {
  name: string
  deptId?: number
  dbType: string
  host: string
  port: number
  driverClassName?: string
  status?: number
  description?: string
}) {
  return http.post(`${MANAGE_BASE}/instances`, data) as Promise<ApiResponse<InstanceView>>
}

export function updateInstance(
  id: number,
  data: {
    name: string
    deptId?: number
    dbType: string
    host: string
    port: number
    driverClassName?: string
    status?: number
    description?: string
  },
) {
  return http.put(`${MANAGE_BASE}/instances/${id}`, data) as Promise<ApiResponse<InstanceView>>
}

export function deleteInstance(id: number) {
  return http.delete(`${MANAGE_BASE}/instances/${id}`) as Promise<ApiResponse<null>>
}

export function uploadInstanceDriver(id: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return http.post(`${MANAGE_BASE}/instances/${id}/driver`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }) as Promise<ApiResponse<InstanceView>>
}

export function listConnections() {
  return http.get(`${MANAGE_BASE}/connections`) as Promise<ApiResponse<ConnectionView[]>>
}

export function createConnection(data: {
  name: string
  deptId?: number
  instanceId: number
  username: string
  password: string
  initialDatabase?: string
  status?: number
}) {
  return http.post(`${MANAGE_BASE}/connections`, data) as Promise<ApiResponse<ConnectionView>>
}

export function pingConnection(data: {
  connectionId?: number
  instanceId: number
  username: string
  password?: string
  initialDatabase?: string
}) {
  return http.post(`${MANAGE_BASE}/connections/ping`, data) as Promise<
    ApiResponse<{ success: boolean; latencyMs: number; message: string }>
  >
}

export function updateConnection(
  id: number,
  data: {
    name: string
    deptId?: number
    instanceId: number
    username: string
    password?: string
    initialDatabase?: string
    status?: number
  },
) {
  return http.put(`${MANAGE_BASE}/connections/${id}`, data) as Promise<ApiResponse<ConnectionView>>
}

export function deleteConnection(id: number) {
  return http.delete(`${MANAGE_BASE}/connections/${id}`) as Promise<ApiResponse<null>>
}
