import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { MANAGE_BASE } from '@/modules/manage/constants'

/** @deprecated 兼容旧字段，请使用 ObjectRef */
export interface TableRef {
  schema?: string
  name: string
}

export interface ObjectRef {
  database?: string
  schema?: string
  name?: string
}

export type ObjectScopeCode = 'CONNECTION' | 'DATABASE' | 'SCHEMA' | 'TABLE'

export interface GrantTarget {
  connectionId: number
  objectScope: ObjectScopeCode
  objects?: ObjectRef[]
}

export interface WorkspaceListItem {
  id: number
  name: string
  description?: string | null
  ownerUserId: number
  spaceType?: string
  myRole: string
  memberCount: number
  assetCount: number
  updatedAt?: string
}

export interface WorkspaceMember {
  id: number
  userId: number
  roleCode: string
  joinedAt?: string
}

export interface WorkspaceAsset {
  id: number
  connectionId: number
  connectionName: string
  objectScope: string
  objects?: ObjectRef[]
  /** @deprecated 兼容旧响应 */
  tables?: ObjectRef[]
  ops: string[]
  createdBy?: number
  createdAt?: string
}

export interface WorkspaceMemberGrant {
  id: number
  userId: number
  grantMode: string
  connectionId?: number | null
  connectionName?: string | null
  objectScope?: string | null
  objects?: ObjectRef[]
  /** @deprecated 兼容旧响应 */
  tables?: ObjectRef[]
  ops?: string[]
  createdBy?: number
  createdAt?: string
}

export interface WorkspaceDetail {
  id: number
  name: string
  description?: string | null
  ownerUserId: number
  spaceType?: string
  myRole?: string | null
  updatedAt?: string
  members: WorkspaceMember[]
  assets: WorkspaceAsset[]
  memberGrants: WorkspaceMemberGrant[]
}

export function listMyWorkspaces() {
  return http.get(`${MANAGE_BASE}/workspaces/mine`) as Promise<ApiResponse<WorkspaceListItem[]>>
}

export function getPersonalWorkspace() {
  return http.get(`${MANAGE_BASE}/workspaces/personal`) as Promise<ApiResponse<WorkspaceListItem | null>>
}

export function ensurePersonalWorkspace(data?: { name?: string; description?: string }) {
  return http.post(`${MANAGE_BASE}/workspaces/personal`, data || {}) as Promise<
    ApiResponse<{ id: number; name: string; spaceType?: string }>
  >
}

export function getWorkspace(id: number) {
  return http.get(`${MANAGE_BASE}/workspaces/${id}`) as Promise<ApiResponse<WorkspaceDetail>>
}

export function createWorkspace(data: { name: string; description?: string }) {
  return http.post(`${MANAGE_BASE}/workspaces`, data) as Promise<ApiResponse<{ id: number; name: string }>>
}

export function addMembers(workspaceId: number, userIds: number[]) {
  return http.post(`${MANAGE_BASE}/workspaces/${workspaceId}/members`, { userIds }) as Promise<
    ApiResponse<null>
  >
}

export function setMemberRole(workspaceId: number, userId: number, roleCode: string) {
  return http.put(`${MANAGE_BASE}/workspaces/${workspaceId}/members/${userId}/role`, {
    roleCode,
  }) as Promise<ApiResponse<null>>
}

export function removeMember(workspaceId: number, userId: number) {
  return http.delete(`${MANAGE_BASE}/workspaces/${workspaceId}/members/${userId}`) as Promise<
    ApiResponse<null>
  >
}

export function addAsset(
  workspaceId: number,
  data: {
    connectionId: number
    objectScope: ObjectScopeCode | string
    objects?: ObjectRef[]
    /** @deprecated 兼容旧调用 */
    tables?: ObjectRef[]
    ops: string[]
  },
) {
  return http.post(`${MANAGE_BASE}/workspaces/${workspaceId}/assets`, data) as Promise<ApiResponse<null>>
}

export function removeAsset(workspaceId: number, assetId: number) {
  return http.delete(`${MANAGE_BASE}/workspaces/${workspaceId}/assets/${assetId}`) as Promise<
    ApiResponse<null>
  >
}

export function addMemberGrant(
  workspaceId: number,
  data: {
    userId: number
    grantMode: string
    connectionId?: number
    objectScope?: ObjectScopeCode | string
    objects?: ObjectRef[]
    tables?: ObjectRef[]
    ops?: string[]
  },
) {
  return http.post(`${MANAGE_BASE}/workspaces/${workspaceId}/member-grants`, data) as Promise<
    ApiResponse<null>
  >
}

export function batchMemberGrants(
  workspaceId: number,
  data: {
    userIds: number[]
    targets: GrantTarget[]
    ops: string[]
  },
) {
  return http.post(`${MANAGE_BASE}/workspaces/${workspaceId}/member-grants/batch`, data) as Promise<
    ApiResponse<null>
  >
}

export function removeMemberGrant(workspaceId: number, grantId: number) {
  return http.delete(`${MANAGE_BASE}/workspaces/${workspaceId}/member-grants/${grantId}`) as Promise<
    ApiResponse<null>
  >
}
