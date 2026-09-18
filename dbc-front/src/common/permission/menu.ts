/**
 * 权限码工具与菜单过滤插件（跨模块可复用）。
 * 判定只看用户已绑定的权限码（含 view←operate 蕴含），不按角色编码硬编码放行。
 */

/** 判断是否拥有 required；view 可被同功能 operate 满足 */
export function impliesPermission(owned: string[] | undefined | null, required: string): boolean {
  if (!owned?.length || !required) return false
  if (owned.includes(required)) return true
  if (required.endsWith('.view')) {
    const operate = required.slice(0, -'.view'.length) + '.operate'
    return owned.includes(operate)
  }
  return false
}

export function hasPermission(owned: string[] | undefined | null, required: string): boolean {
  return impliesPermission(owned, required)
}

export function hasAnyPermission(owned: string[] | undefined | null, requiredList: string[]): boolean {
  return requiredList.some((r) => impliesPermission(owned, r))
}

/** 菜单项声明（插件输入） */
export interface PermissionMenuItem {
  key: string
  label: string
  path?: string
  /** 显示所需权限（通常为 *.view） */
  permission?: string
  children?: PermissionMenuItem[]
}

/**
 * 按权限过滤菜单树；无 permission 字段的节点始终保留（如纯分组需自带权限）。
 */
export function filterMenusByPermission(
  menus: PermissionMenuItem[],
  owned: string[] | undefined | null,
): PermissionMenuItem[] {
  const result: PermissionMenuItem[] = []
  for (const item of menus) {
    const children = item.children
      ? filterMenusByPermission(item.children, owned)
      : undefined
    const selfOk = !item.permission || impliesPermission(owned, item.permission)
    if (children && children.length > 0) {
      result.push({ ...item, children })
    } else if (selfOk && (!item.children || item.children.length === 0)) {
      result.push({ ...item, children: undefined })
    }
  }
  return result
}

/** 用户中心侧栏菜单定义 */
export const USER_CENTER_SIDE_MENUS: PermissionMenuItem[] = [
  { key: 'users', label: '用户管理', path: '/user-center/users', permission: 'usercenter.user.view' },
  { key: 'depts', label: '部门管理', path: '/user-center/depts', permission: 'usercenter.dept.view' },
  { key: 'roles', label: '角色管理', path: '/user-center/roles', permission: 'usercenter.role.view' },
  {
    key: 'permissions',
    label: '权限管理',
    path: '/user-center/permissions',
    permission: 'usercenter.permission.view',
  },
]

/** 是否具备用户中心任一功能权限（用于顶栏显示） */
export const USER_CENTER_ANY_VIEW = [
  'usercenter.user.view',
  'usercenter.dept.view',
  'usercenter.role.view',
  'usercenter.permission.view',
]
