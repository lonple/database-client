export const SQLWORK_BASE = '/dbc-sqlwork'

export const ROLE_LABELS: Record<string, string> = {
  OWNER: '所有者',
  ADMIN: '空间管理员',
  OPERATOR: '数据操作人员',
}

export const DML_OPS = ['SELECT', 'INSERT', 'UPDATE', 'DELETE'] as const
export const DDL_OPS = ['CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'COMMENT', 'INDEX'] as const
