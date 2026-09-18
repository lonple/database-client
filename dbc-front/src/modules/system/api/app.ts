import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'

export interface AppView {
  id: number
  clientId: string
  appName: string
  builtin: number
  status: number
  hasClientCert: boolean
  createdAt?: string
  updatedAt?: string
}

export interface AppKeyView {
  id: number
  clientId: string
  kid: string
  algorithm: string
  publicKeyPem: string
  instanceId?: string
  status: string
  alive?: boolean
  createdAt?: string
  lastSeenAt?: string
  revokedAt?: string
}

export function listApps() {
  return http.get(`${USER_CENTER_BASE}/apps`) as Promise<ApiResponse<AppView[]>>
}

export function createApp(data: { clientId: string; appName: string }) {
  return http.post(`${USER_CENTER_BASE}/apps`, data) as Promise<ApiResponse<AppView>>
}

export function updateAppStatus(id: number, status: number) {
  return http.put(`${USER_CENTER_BASE}/apps/${id}/status`, null, {
    params: { status },
  }) as Promise<ApiResponse<AppView>>
}

export function reissueAppCert(id: number) {
  return http.post(`${USER_CENTER_BASE}/apps/${id}/reissue-cert`) as Promise<ApiResponse<null>>
}

export function listAppKeys(id: number) {
  return http.get(`${USER_CENTER_BASE}/apps/${id}/keys`) as Promise<ApiResponse<AppKeyView[]>>
}

export function revokeAppKey(id: number, kid: string) {
  return http.post(`${USER_CENTER_BASE}/apps/${id}/keys/${encodeURIComponent(kid)}/revoke`) as Promise<
    ApiResponse<null>
  >
}

export function rotateSelfSigningKey() {
  return http.post(`${USER_CENTER_BASE}/apps/self/rotate-signing-key`) as Promise<ApiResponse<AppKeyView>>
}

export function probeInnerPing() {
  return http.post(`${USER_CENTER_BASE}/apps/self/probe-inner-ping`) as Promise<
    ApiResponse<{ status: number; kid: string; body: string }>
  >
}
