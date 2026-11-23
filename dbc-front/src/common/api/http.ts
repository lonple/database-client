/**
 * 统一 HTTP 客户端（全站共用）。
 * 业务请求：Bearer access（内存）；refresh/logout 走 auth API（Cookie + CSRF）。
 */
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'

const http = axios.create({
  timeout: 15000,
})

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean }

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  const domain = useDomainStore()
  config.headers['X-Dbc-Domain'] = domain.domain
  return config
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      message.error(body.message || '请求失败')
      return Promise.reject(body)
    }
    return body
  },
  async (error: AxiosError) => {
    const status = error.response?.status
    const data = error.response?.data as { message?: string; error?: string } | undefined
    const config = error.config as RetriableConfig | undefined
    const msg =
      (typeof data?.message === 'string' && data.message) ||
      (status === 503 ? '服务暂不可用' : '') ||
      (typeof data?.error === 'string' && data.error) ||
      error.message ||
      '网络错误'

    if (status === 401 && config && !config._retry) {
      const auth = useAuthStore()
      config._retry = true
      const ok = await auth.refreshAccess()
      if (ok && auth.accessToken) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${auth.accessToken}`
        return http.request(config)
      }
      auth.clear()
      if (router.currentRoute.value.path !== '/login') {
        router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    message.error(msg)
    return Promise.reject(error)
  },
)

export default http
