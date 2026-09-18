/**
 * 统一 HTTP 客户端（全站共用）。
 */
import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'

const http = axios.create({
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
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
  (error) => {
    const status = error.response?.status
    const msg = error.response?.data?.message || error.message || '网络错误'
    if (status === 401) {
      const auth = useAuthStore()
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
