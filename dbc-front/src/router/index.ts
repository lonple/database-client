import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { homeRoutes } from '@/modules/home/routes'
import { userCenterRoutes } from '@/modules/user-center/routes'
import { systemRoutes } from '@/modules/system/routes'
import { manageRoutes } from '@/modules/manage/routes'
import { authRoutes } from '@/modules/auth/routes'
import { sqlworkRoutes } from '@/modules/sqlwork/routes'
import { auditRoutes } from '@/modules/audit/routes'
import { hasPermission } from '@/common/permission/menu'

/** 个人域下可用 personal.space.view 替代的 manage 权限 */
const PERSONAL_DOMAIN_MANAGE_PERMS = new Set([
  'manage.instance.view',
  'manage.instance.operate',
  'manage.connection.view',
  'manage.connection.operate',
  'auth.workspace.view',
  'auth.workspace.operate',
])

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/home' },
    ...homeRoutes,
    ...userCenterRoutes,
    ...systemRoutes,
    ...manageRoutes,
    ...authRoutes,
    ...sqlworkRoutes,
    ...auditRoutes,
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const domain = useDomainStore()
  if (to.meta.public) {
    if (auth.token && to.path === '/login') return '/home'
    return true
  }
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!auth.user) {
    try {
      await auth.loadMe()
    } catch {
      auth.clear()
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  if (to.meta.superAdmin) {
    const ok = !!auth.user?.roles?.some((r) => r.code === 'SUPER_ADMIN')
    if (!ok) return '/home'
  }
  if (domain.isPersonal && to.path.startsWith('/manage/auth/global-policies')) {
    return '/manage/auth/workspaces'
  }
  if (domain.isPersonal && (to.path.startsWith('/user-center') || to.path.startsWith('/system'))) {
    return '/home'
  }
  const required = typeof to.meta.permission === 'string' ? to.meta.permission : ''
  if (required) {
    const owned = auth.user?.permissions
    const ok =
      hasPermission(owned, required) ||
      (domain.isPersonal &&
        PERSONAL_DOMAIN_MANAGE_PERMS.has(required) &&
        hasPermission(owned, 'usercenter.personal.space.view'))
    if (!ok) return '/home'
  }
  return true
})

export default router
