import type { RouteRecordRaw } from 'vue-router'
import { USER_CENTER_SIDE_MENUS } from '@/common/permission/menu'

/** 用户中心模块路由 */
export const userCenterRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/modules/user-center/views/login/LoginView.vue'),
    meta: { public: true, module: 'user-center' },
  },
  {
    path: '/user-center',
    component: () => import('@/layouts/WorkbenchLayout.vue'),
    redirect: '/user-center/users',
    meta: { module: 'user-center' },
    children: [
      {
        path: 'users',
        name: 'users',
        component: () => import('@/modules/user-center/views/user/UserListView.vue'),
        meta: { module: 'user-center', title: '用户管理', permission: 'usercenter.user.view' },
      },
      {
        path: 'depts',
        name: 'depts',
        component: () => import('@/modules/user-center/views/dept/DeptManageView.vue'),
        meta: { module: 'user-center', title: '部门管理', permission: 'usercenter.dept.view' },
      },
      {
        path: 'roles',
        name: 'roles',
        component: () => import('@/modules/user-center/views/role/RoleListView.vue'),
        meta: { module: 'user-center', title: '角色管理', permission: 'usercenter.role.view' },
      },
      {
        path: 'permissions',
        name: 'permissions',
        component: () => import('@/modules/user-center/views/permission/PermissionListView.vue'),
        meta: { module: 'user-center', title: '权限管理', permission: 'usercenter.permission.view' },
      },
    ],
  },
]

/** @deprecated 请使用 common/permission 中的 USER_CENTER_SIDE_MENUS + filterMenusByPermission */
export const userCenterSideMenus = USER_CENTER_SIDE_MENUS
