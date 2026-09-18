import { DDL_OPS, DML_OPS } from '@/modules/sqlwork/constants'

const ALL_SQL_OPS = [...DML_OPS, ...DDL_OPS] as string[]

/** 列表展示：全选时显示「全部权限」，否则逐项标签文案。 */
export function formatSqlOps(ops?: string[] | null): string[] {
  if (!ops || !ops.length) return []
  const set = new Set(ops.map((o) => String(o).toUpperCase()))
  const selected = ALL_SQL_OPS.filter((op) => set.has(op))
  if (selected.length === ALL_SQL_OPS.length) {
    return ['全部权限']
  }
  return selected.length ? selected : ops
}

export { ALL_SQL_OPS }
