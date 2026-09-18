import type { RouteRecordRaw } from 'vue-router'
import type { PermissionMenuItem } from '@/common/permission/menu'

/**
 * 权限管控模块路由（独立业务模块；API 仍走 /dbc-manage）。
 * URL 保持 /manage/auth/* 与既有书签兼容。
 */
export const authRoutes: RouteRecordRaw[] = [
  {
    path: '/manage/auth',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    redirect: '/manage/auth/workspaces',
    meta: { module: 'auth' },
    children: [
      {
        path: 'global-policies',
        name: 'manage-auth-global-policies',
        component: () => import('@/modules/auth/views/GlobalPolicyListView.vue'),
        meta: {
          module: 'auth',
          title: '全局管控',
          permission: 'auth.global.policy.view',
        },
      },
      {
        path: 'workspaces',
        name: 'manage-auth-workspaces',
        component: () => import('@/modules/auth/views/WorkspaceListView.vue'),
        meta: {
          module: 'auth',
          title: '工作空间授权',
          permission: 'auth.workspace.view',
        },
      },
      {
        path: 'workspaces/:id',
        name: 'manage-auth-workspace-detail',
        component: () => import('@/modules/auth/views/WorkspaceDetailView.vue'),
        meta: {
          module: 'auth',
          title: '工作空间详情',
          permission: 'auth.workspace.view',
        },
      },
    ],
  },
]

/** 权限管控侧栏 */
export const AUTH_SIDE_MENUS: PermissionMenuItem[] = [
  {
    key: 'manage-auth-global-policies',
    label: '全局管控',
    path: '/manage/auth/global-policies',
    permission: 'auth.global.policy.view',
  },
  {
    key: 'manage-auth-workspaces',
    label: '工作空间授权',
    path: '/manage/auth/workspaces',
    permission: 'auth.workspace.view',
  },
]

export const AUTH_ANY_VIEW = [
  'auth.workspace.view',
  'auth.global.policy.view',
]
