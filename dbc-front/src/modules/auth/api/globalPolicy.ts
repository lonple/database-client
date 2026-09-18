import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { MANAGE_BASE } from '@/modules/manage/constants'

export type GlobalPolicy = {
  id: number
  name: string
  ops: string[]
  strategy: 'BLOCK' | 'ALERT' | 'REAUTH' | string
  workspaceScope: 'ALL' | 'SPECIFIC' | string
  workspaceIds: number[]
  sortNo: number
  status: number
  updatedAt?: string
}

export type GlobalPolicySave = {
  name: string
  ops: string[]
  strategy: string
  workspaceScope: string
  workspaceIds?: number[]
  sortNo?: number
  status: number
}

export function listGlobalPolicies() {
  return http.get(`${MANAGE_BASE}/auth/global-policies`) as Promise<ApiResponse<GlobalPolicy[]>>
}

export function createGlobalPolicy(body: GlobalPolicySave) {
  return http.post(`${MANAGE_BASE}/auth/global-policies`, body) as Promise<ApiResponse<GlobalPolicy>>
}

export function updateGlobalPolicy(id: number, body: GlobalPolicySave) {
  return http.put(`${MANAGE_BASE}/auth/global-policies/${id}`, body) as Promise<ApiResponse<GlobalPolicy>>
}

export function deleteGlobalPolicy(id: number) {
  return http.delete(`${MANAGE_BASE}/auth/global-policies/${id}`) as Promise<ApiResponse<null>>
}
