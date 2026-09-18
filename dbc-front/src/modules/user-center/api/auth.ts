import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import type { UserView } from '@/modules/user-center/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'

export function login(username: string, password: string) {
  return http.post(`${USER_CENTER_BASE}/auth/login`, { username, password }) as Promise<
    ApiResponse<{ token: string; expiresIn: number; user: UserView }>
  >
}

export function fetchMe() {
  return http.get(`${USER_CENTER_BASE}/auth/me`) as Promise<ApiResponse<UserView>>
}

export function logout() {
  return http.post(`${USER_CENTER_BASE}/auth/logout`) as Promise<ApiResponse<null>>
}
