import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'
import type { RoleView } from '@/modules/user-center/api/types'

export function fetchRoles() {
  return http.get(`${USER_CENTER_BASE}/roles`) as Promise<ApiResponse<RoleView[]>>
}

export function fetchRole(id: number) {
  return http.get(`${USER_CENTER_BASE}/roles/${id}`) as Promise<ApiResponse<RoleView>>
}

export function createRole(data: {
  code: string
  name: string
  description?: string
  dataScope: string
  deptIds?: number[]
}) {
  return http.post(`${USER_CENTER_BASE}/roles`, data) as Promise<ApiResponse<RoleView>>
}

export function updateRole(
  id: number,
  data: { name: string; description?: string; dataScope: string; deptIds?: number[] },
) {
  return http.put(`${USER_CENTER_BASE}/roles/${id}`, data) as Promise<ApiResponse<RoleView>>
}

export function deleteRole(id: number) {
  return http.delete(`${USER_CENTER_BASE}/roles/${id}`) as Promise<ApiResponse<null>>
}
