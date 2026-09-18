import type { RouteRecordRaw } from 'vue-router'

/** 首页模块路由 */
export const homeRoutes: RouteRecordRaw[] = [
  {
    path: '/home',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    meta: { module: 'home' },
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/modules/home/views/WelcomeView.vue'),
        meta: { module: 'home', title: '首页' },
      },
    ],
  },
]
