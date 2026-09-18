import { computed } from 'vue'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { hasPermission as check, hasAnyPermission as checkAny } from '@/common/permission/menu'

/** 当前登录用户权限判断（仅依据 /me 返回的权限码） */
export function usePermission() {
  const auth = useAuthStore()
  const permissions = computed(() => auth.user?.permissions || [])

  function hasPermission(code: string) {
    return check(permissions.value, code)
  }

  function hasAnyPermission(codes: string[]) {
    return checkAny(permissions.value, codes)
  }

  return { permissions, hasPermission, hasAnyPermission }
}
