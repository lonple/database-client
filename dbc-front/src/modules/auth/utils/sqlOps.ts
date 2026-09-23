import { DDL_OPS, DML_OPS } from '@/modules/sqlwork/constants'

/** 任意 SQL 哨兵：含 OTHER 等未在 DML/DDL 枚举中的语句；≠ 勾选全部具名 DML+DDL */
export const SQL_OP_ANY = 'ANY'

const ALL_SQL_OPS = [...DML_OPS, ...DDL_OPS] as string[]

export function isAnyOp(op?: string | null): boolean {
  return String(op || '').trim().toUpperCase() === SQL_OP_ANY
}

export function includesAnyOp(ops?: string[] | null): boolean {
  return (ops || []).some((o) => isAnyOp(o))
}

/** 写入规范：含 ANY 时折叠为 ['ANY'] */
export function normalizeSqlOps(ops?: string[] | null): string[] {
  if (!ops?.length) return []
  if (includesAnyOp(ops)) return [SQL_OP_ANY]
  const set = new Set(ops.map((o) => String(o).toUpperCase()).filter(Boolean))
  return ALL_SQL_OPS.filter((op) => set.has(op))
}

/** 列表展示：ANY →「任意 SQL」；否则具名列表；全具名仍逐项显示（不等于任意） */
export function formatSqlOps(ops?: string[] | null): string[] {
  if (!ops || !ops.length) return []
  if (includesAnyOp(ops)) return ['任意 SQL']
  const set = new Set(ops.map((o) => String(o).toUpperCase()))
  const selected = ALL_SQL_OPS.filter((op) => set.has(op))
  return selected.length ? selected : ops
}

export { ALL_SQL_OPS }
