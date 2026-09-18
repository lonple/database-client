import http from '@/common/api/http'
import type { ApiResponse, PageResult } from '@/common/api/types'
import type { UserView } from '@/modules/user-center/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'
export { fetchRoles } from '@/modules/user-center/api/role'

export function fetchUsers(params: { page: number; size: number; username?: string }) {
  return http.get(`${USER_CENTER_BASE}/users`, { params }) as Promise<ApiResponse<PageResult<UserView>>>
}

export function createUser(data: {
  username: string
  password: string
  roleIds: number[]
  deptId?: number | null
  mobile?: string
  description?: string
  status: number
}) {
  return http.post(`${USER_CENTER_BASE}/users`, data) as Promise<ApiResponse<UserView>>
}

export function updateUser(
  id: number,
  data: {
    roleIds: number[]
    deptId?: number | null
    mobile?: string
    description?: string
    status: number
  },
) {
  return http.put(`${USER_CENTER_BASE}/users/${id}`, data) as Promise<ApiResponse<UserView>>
}

export function deleteUser(id: number) {
  return http.delete(`${USER_CENTER_BASE}/users/${id}`) as Promise<ApiResponse<null>>
}

export function resetPassword(id: number, password: string) {
  return http.put(`${USER_CENTER_BASE}/users/${id}/password`, { password }) as Promise<ApiResponse<null>>
}
