import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'
import type { DeptTreeNode, DeptView } from '@/modules/user-center/api/types'

export function fetchDeptTree() {
  return http.get(`${USER_CENTER_BASE}/depts/tree`) as Promise<ApiResponse<DeptTreeNode[]>>
}

export function fetchDept(id: number) {
  return http.get(`${USER_CENTER_BASE}/depts/${id}`) as Promise<ApiResponse<DeptView>>
}

export function createDept(data: { name: string; description?: string; parentId: number }) {
  return http.post(`${USER_CENTER_BASE}/depts`, data) as Promise<ApiResponse<DeptView>>
}

export function updateDept(
  id: number,
  data: { name: string; description?: string; parentId?: number | null },
) {
  return http.put(`${USER_CENTER_BASE}/depts/${id}`, data) as Promise<ApiResponse<DeptView>>
}

export function deleteDept(id: number) {
  return http.delete(`${USER_CENTER_BASE}/depts/${id}`) as Promise<ApiResponse<null>>
}
