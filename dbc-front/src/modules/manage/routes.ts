import type { RouteRecordRaw } from 'vue-router'
import type { PermissionMenuItem } from '@/common/permission/menu'

/** 资产管理模块路由（仅实例/连接；API 走 /dbc-manage） */
export const manageRoutes: RouteRecordRaw[] = [
  {
    path: '/manage',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    redirect: '/manage/instances',
    meta: { module: 'manage' },
    children: [
      {
        path: 'instances',
        name: 'manage-instances',
        component: () => import('@/modules/manage/views/InstanceListView.vue'),
        meta: { module: 'manage', title: '实例管理', permission: 'manage.instance.view' },
      },
      {
        path: 'connections',
        name: 'manage-connections',
        component: () => import('@/modules/manage/views/ConnectionListView.vue'),
        meta: { module: 'manage', title: '连接管理', permission: 'manage.connection.view' },
      },
    ],
  },
]

/** 资产管理侧栏 */
export const MANAGE_SIDE_MENUS: PermissionMenuItem[] = [
  {
    key: 'manage-instances',
    label: '实例管理',
    path: '/manage/instances',
    permission: 'manage.instance.view',
  },
  {
    key: 'manage-connections',
    label: '连接管理',
    path: '/manage/connections',
    permission: 'manage.connection.view',
  },
]

export const MANAGE_ANY_VIEW = ['manage.instance.view', 'manage.connection.view']
