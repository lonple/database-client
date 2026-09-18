import type { RouteRecordRaw } from 'vue-router'
import type { PermissionMenuItem } from '@/common/permission/menu'

/** SQL 工作台路由 */
export const sqlworkRoutes: RouteRecordRaw[] = [
  {
    path: '/sqlwork',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    meta: { module: 'sqlwork' },
    children: [
      {
        path: '',
        name: 'sqlwork-pick',
        component: () => import('@/modules/sqlwork/views/SqlworkPickView.vue'),
        meta: {
          module: 'sqlwork',
          title: 'SQL 工作台',
          permission: 'sqlwork.execute',
          fullContent: true,
        },
      },
      {
        path: 'workspace/:id',
        name: 'sqlwork-editor',
        component: () => import('@/modules/sqlwork/views/SqlworkEditorView.vue'),
        meta: {
          module: 'sqlwork',
          title: 'SQL 工作台',
          permission: 'sqlwork.execute',
          fullContent: true,
        },
      },
    ],
  },
]

export const SQLWORK_ANY_VIEW = ['sqlwork.execute', 'sqlwork.meta.view']

export const SQLWORK_SIDE_MENUS: PermissionMenuItem[] = []
