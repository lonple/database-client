import type { RouteRecordRaw } from 'vue-router'
import type { PermissionMenuItem } from '@/common/permission/menu'

export const auditRoutes: RouteRecordRaw[] = [
  {
    path: '/audit',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    redirect: '/audit/sql-logs',
    meta: { module: 'audit' },
    children: [
      {
        path: 'biz-logs',
        name: 'audit-biz-logs',
        component: () => import('@/modules/audit/views/BizLogListView.vue'),
        meta: {
          module: 'audit',
          title: '业务日志',
          permission: 'audit.biz.view',
        },
      },
      {
        path: 'sql-logs',
        name: 'audit-sql-logs',
        component: () => import('@/modules/audit/views/SqlLogListView.vue'),
        meta: {
          module: 'audit',
          title: 'SQL 操作日志',
          permission: 'audit.sql.view',
        },
      },
      {
        path: 'askdata-monitor',
        name: 'audit-askdata-monitor',
        component: () => import('@/modules/audit/views/AskdataMonitorView.vue'),
        meta: {
          module: 'audit',
          title: '智能问数监控',
          permission: 'audit.askdata.view',
        },
      },
    ],
  },
]

export const AUDIT_SIDE_MENUS: PermissionMenuItem[] = [
  {
    key: 'audit-biz-logs',
    label: '业务日志',
    path: '/audit/biz-logs',
    permission: 'audit.biz.view',
  },
  {
    key: 'audit-sql-logs',
    label: 'SQL 操作日志',
    path: '/audit/sql-logs',
    permission: 'audit.sql.view',
  },
  {
    key: 'audit-askdata-monitor',
    label: '智能问数监控',
    path: '/audit/askdata-monitor',
    permission: 'audit.askdata.view',
  },
]

export const AUDIT_ANY_VIEW = ['audit.biz.view', 'audit.sql.view', 'audit.askdata.view']
