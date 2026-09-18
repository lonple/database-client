import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import type { PermissionModuleView, PermissionView } from '@/modules/user-center/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'

export function fetchPermissionModules() {
  return http.get(`${USER_CENTER_BASE}/permissions`) as Promise<ApiResponse<PermissionModuleView[]>>
}

export function fetchAllPermissions() {
  return http.get(`${USER_CENTER_BASE}/permissions/all`) as Promise<ApiResponse<PermissionView[]>>
}

export function fetchRolePermissionIds(roleId: number) {
  return http.get(`${USER_CENTER_BASE}/roles/${roleId}/permissions`) as Promise<ApiResponse<number[]>>
}

export function updateRolePermissions(roleId: number, permissionIds: number[]) {
  return http.put(`${USER_CENTER_BASE}/roles/${roleId}/permissions`, { permissionIds }) as Promise<
    ApiResponse<null>
  >
}
