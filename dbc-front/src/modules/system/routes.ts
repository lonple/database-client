import type { RouteRecordRaw } from 'vue-router'

/** 系统管理模块路由（仅超管） */
export const systemRoutes: RouteRecordRaw[] = [
  {
    path: '/system',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    redirect: '/system/apps',
    meta: { module: 'system', superAdmin: true },
    children: [
      {
        path: 'apps',
        name: 'system-apps',
        component: () => import('@/modules/system/views/AppManageView.vue'),
        meta: { module: 'system', title: '应用管理', superAdmin: true },
      },
      {
        path: 'app-config',
        name: 'system-app-config',
        component: () => import('@/modules/system/views/AppConfigView.vue'),
        meta: { module: 'system', title: '应用配置', superAdmin: true },
      },
    ],
  },
]

export const SYSTEM_SIDE_MENUS = [
  { key: 'system-apps', label: '应用管理', path: '/system/apps' },
  { key: 'system-app-config', label: '应用配置', path: '/system/app-config' },
]
