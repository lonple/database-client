import axios from 'axios'
import http from '@/common/api/http'
import type { ApiResponse } from '@/common/api/types'
import type { UserView } from '@/modules/user-center/api/types'
import { USER_CENTER_BASE } from '@/modules/user-center/constants'
import { readCsrfCookie } from '@/modules/user-center/stores/sessionCookies'

export type TokenResponse = {
  accessToken: string
  expiresIn: number
  user: UserView | null
}

/** 登录：需携带 credentials 以接收 refresh/csrf Cookie */
export function login(username: string, password: string) {
  return axios
    .post(`${USER_CENTER_BASE}/auth/login`, { username, password }, { withCredentials: true, timeout: 15000 })
    .then((resp) => {
      const body = resp.data
      if (body && typeof body.code === 'number' && body.code !== 0) {
        return Promise.reject(body)
      }
      return body as ApiResponse<TokenResponse>
    })
}

/** 刷新 access：Cookie + CSRF；不走统一 http（避免 401 环） */
export function refresh() {
  const csrf = readCsrfCookie()
  return axios
    .post(
      `${USER_CENTER_BASE}/auth/refresh`,
      {},
      {
        withCredentials: true,
        timeout: 15000,
        headers: csrf ? { 'X-Dbc-CSRF': csrf } : {},
      },
    )
    .then((resp) => {
      const body = resp.data
      if (body && typeof body.code === 'number' && body.code !== 0) {
        return Promise.reject(body)
      }
      return body as ApiResponse<TokenResponse>
    })
}

export function fetchMe() {
  return http.get(`${USER_CENTER_BASE}/auth/me`) as Promise<ApiResponse<UserView>>
}

export function logout() {
  const csrf = readCsrfCookie()
  return axios
    .post(
      `${USER_CENTER_BASE}/auth/logout`,
      {},
      {
        withCredentials: true,
        timeout: 15000,
        headers: csrf ? { 'X-Dbc-CSRF': csrf } : {},
      },
    )
    .then((resp) => {
      const body = resp.data
      if (body && typeof body.code === 'number' && body.code !== 0) {
        return Promise.reject(body)
      }
      return body as ApiResponse<null>
    })
}
