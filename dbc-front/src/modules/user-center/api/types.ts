/** 用户中心模块 API 类型 */

export interface RoleBrief {
  id: number
  code: string
  name: string
  description?: string
  dataScope?: string
  builtin?: boolean
}

export interface RoleView extends RoleBrief {
  deptIds?: number[]
}

export interface UserView {
  id: number
  username: string
  mobile?: string | null
  description?: string | null
  status: number
  builtin: boolean
  createdAt?: string
  deptId?: number | null
  deptName?: string | null
  roles: RoleBrief[]
  role?: RoleBrief
  permissions?: string[]
}

export interface PermissionView {
  id: number
  code: string
  name: string
  description?: string | null
  moduleCode: string
  moduleName: string
  featureCode: string
  featureName: string
  sortNo?: number
  builtin?: boolean
}

export interface PermissionModuleView {
  moduleCode: string
  moduleName: string
  permissions: PermissionView[]
}

export interface DeptTreeNode {
  id: number
  name: string
  description?: string | null
  parentId?: number | null
  level: number
  path: string
  children?: DeptTreeNode[]
}

export interface DeptView {
  id: number
  name: string
  description?: string | null
  parentId?: number | null
  parentName?: string | null
  level: number
  path: string
  root: boolean
}

export const DATA_SCOPE_OPTIONS = [
  { value: 'ALL', label: '全公司' },
  { value: 'DEPT_AND_CHILDREN', label: '当前部门及子部门' },
  { value: 'DEPT_ONLY', label: '仅当前部门' },
  { value: 'CUSTOM', label: '自定义部门' },
]

export function dataScopeLabel(code?: string) {
  return DATA_SCOPE_OPTIONS.find((o) => o.value === code)?.label || code || '-'
}
