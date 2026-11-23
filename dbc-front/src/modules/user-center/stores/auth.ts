import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UserView } from '@/modules/user-center/api/types'
import * as authApi from '@/modules/user-center/api/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { publishAuthSync, subscribeAuthSync } from '@/modules/user-center/stores/authSync'

/** 用户中心：认证状态。accessToken 仅内存，禁止 localStorage。 */
export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserView | null>(null)
  /** @deprecated 兼容旧引用，等同 accessToken */
  const token = accessToken

  let refreshPromise: Promise<boolean> | null = null
  let syncBound = false

  function bindSync() {
    if (syncBound || typeof window === 'undefined') return
    syncBound = true
    subscribeAuthSync((msg) => {
      if (msg.type === 'access') {
        accessToken.value = msg.accessToken
      } else if (msg.type === 'logout') {
        accessToken.value = null
        user.value = null
        useDomainStore().clear()
      }
    })
  }

  function setAccessToken(next: string | null, broadcast = true) {
    accessToken.value = next
    if (broadcast) {
      publishAuthSync({ type: 'access', accessToken: next })
    }
  }

  function setSession(newToken: string, newUser: UserView) {
    bindSync()
    setAccessToken(newToken)
    user.value = newUser
  }

  function clear(broadcast = true) {
    accessToken.value = null
    user.value = null
    useDomainStore().clear()
    if (broadcast) {
      publishAuthSync({ type: 'logout' })
    }
  }

  async function loadMe() {
    bindSync()
    if (!accessToken.value) return null
    const resp = await authApi.fetchMe()
    user.value = resp.data
    return resp.data
  }

  /**
   * 单飞刷新 access；多 Tab 经 BroadcastChannel 同步结果。
   * @returns 是否拿到有效 access
   */
  async function refreshAccess(): Promise<boolean> {
    bindSync()
    if (refreshPromise) return refreshPromise
    publishAuthSync({ type: 'refresh-start' })
    refreshPromise = (async () => {
      try {
        const resp = await authApi.refresh()
        const next = resp.data?.accessToken
        if (!next) {
          setAccessToken(null)
          publishAuthSync({ type: 'refresh-done', accessToken: null })
          return false
        }
        setAccessToken(next)
        publishAuthSync({ type: 'refresh-done', accessToken: next })
        return true
      } catch {
        setAccessToken(null)
        publishAuthSync({ type: 'refresh-done', accessToken: null })
        return false
      } finally {
        refreshPromise = null
      }
    })()
    return refreshPromise
  }

  /** 路由守卫：无内存 access 时先 refresh，再 loadMe */
  async function ensureSession(): Promise<boolean> {
    bindSync()
    if (!accessToken.value) {
      const ok = await refreshAccess()
      if (!ok) return false
    }
    if (!user.value) {
      try {
        await loadMe()
      } catch {
        const retried = await refreshAccess()
        if (!retried) {
          clear(false)
          return false
        }
        try {
          await loadMe()
        } catch {
          clear(false)
          return false
        }
      }
    }
    return !!accessToken.value && !!user.value
  }

  async function doLogout() {
    try {
      await authApi.logout()
    } finally {
      clear(true)
    }
  }

  return {
    accessToken,
    token,
    user,
    setSession,
    setAccessToken,
    clear,
    loadMe,
    refreshAccess,
    ensureSession,
    doLogout,
  }
})
