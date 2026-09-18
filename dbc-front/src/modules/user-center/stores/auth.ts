import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UserView } from '@/modules/user-center/api/types'
import * as authApi from '@/modules/user-center/api/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'

const TOKEN_KEY = 'dbc_token'

/** 用户中心：认证状态（登录态全站共用，后续可抽到 common） */
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserView | null>(null)

  function setSession(newToken: string, newUser: UserView) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
  }

  function clear() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    useDomainStore().clear()
  }

  async function loadMe() {
    if (!token.value) return null
    const resp = await authApi.fetchMe()
    user.value = resp.data
    return resp.data
  }

  async function doLogout() {
    try {
      if (token.value) await authApi.logout()
    } finally {
      clear()
    }
  }

  return { token, user, setSession, clear, loadMe, doLogout }
})
