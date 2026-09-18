/** 审计详情展示：字段中文名与值格式化 */

const FIELD_LABELS: Record<string, string> = {
  username: '用户名',
  success: '是否成功',
  after: '新建内容',
  changes: '变更项',
  keys: '删除对象',
  id: 'ID',
  name: '名称',
  code: '编码',
  status: '状态',
  email: '邮箱',
  phone: '手机',
  deptId: '部门 ID',
  deptName: '部门',
  roleId: '角色 ID',
  roleIds: '角色',
  displayName: '显示名',
  remark: '备注',
  password: '密码',
  passwordHash: '密码',
  profile: '扩展信息',
  field: '字段',
  before: '变更前',
  denyType: '拒绝类型',
  denyObjects: '拒绝对象',
  missingOps: '缺少权限',
  message: '说明',
  globalPolicy: '全局策略',
  globalPolicyId: '全局策略 ID',
  globalPolicyName: '全局策略名称',
}

const ACTION_LABELS: Record<string, string> = {
  LOGIN: '登录',
  LOGOUT: '退出',
  CREATE: '创建',
  UPDATE: '更新',
  DELETE: '删除',
  CUSTOM: '自定义',
}

export function actionLabel(action?: string): string {
  if (!action) return '-'
  return ACTION_LABELS[action] || action
}

export function fieldLabel(key: string): string {
  if (!key) return '-'
  return FIELD_LABELS[key] || key
}

export function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) return '（空）'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return '（空）'
    // 归一化后的 JSON 字符串再展开为可读文本
    if ((trimmed.startsWith('{') && trimmed.endsWith('}'))
      || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        return formatDisplayValue(JSON.parse(trimmed))
      } catch {
        return value
      }
    }
    return value
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '（空）'
    return value.map((item) => formatDisplayValue(item)).join('、')
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return '（空）'
    return entries
      .map(([k, v]) => `${fieldLabel(k)}：${formatDisplayValue(v)}`)
      .join('；')
  }
  return String(value)
}

export interface ChangeRow {
  field: string
  fieldLabel: string
  before: string
  after: string
}

export function parseChangeRows(details?: Record<string, unknown> | null): ChangeRow[] {
  const raw = details?.changes
  if (!Array.isArray(raw)) return []
  return raw
    .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
    .map((row) => {
      const field = String(row.field ?? '')
      return {
        field,
        fieldLabel: fieldLabel(field),
        before: formatDisplayValue(row.before),
        after: formatDisplayValue(row.after),
      }
    })
}

export function entriesOf(obj?: Record<string, unknown> | null): { key: string; label: string; value: string }[] {
  if (!obj || typeof obj !== 'object') return []
  return Object.entries(obj)
    .filter(([k]) => k !== 'changes' && k !== 'after' && k !== 'keys')
    .map(([key, value]) => ({
      key,
      label: fieldLabel(key),
      value: formatDisplayValue(value),
    }))
}

export function objectEntries(obj: unknown): { key: string; label: string; value: string }[] {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return []
  return Object.entries(obj as Record<string, unknown>).map(([key, value]) => ({
    key,
    label: fieldLabel(key),
    value: formatDisplayValue(value),
  }))
}
