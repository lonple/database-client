import type { RouteRecordRaw } from 'vue-router'

export const askdataRoutes: RouteRecordRaw[] = [
  {
    path: '/askdata',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    meta: { module: 'askdata' },
    children: [
      {
        path: '',
        name: 'askdata-pick',
        component: () => import('@/modules/askdata/views/AskdataPickView.vue'),
        meta: {
          module: 'askdata',
          title: '智能问数',
          permission: 'askdata.use',
          fullContent: true,
        },
      },
      {
        path: 'ws/:workspaceId',
        name: 'askdata-workbench',
        component: () => import('@/modules/askdata/views/AskdataWorkbenchView.vue'),
        meta: {
          module: 'askdata',
          title: '智能问数工作台',
          permission: 'askdata.use',
          fullContent: true,
        },
      },
    ],
  },
]

export const ASKDATA_ANY_VIEW = ['askdata.use']
