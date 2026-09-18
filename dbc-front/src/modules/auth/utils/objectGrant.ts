import type { GrantTarget, ObjectRef, ObjectScopeCode, WorkspaceAsset } from '@/modules/auth/api/workspace'

export type GrantObjectLevel = 'CONNECTION' | 'DATABASE' | 'SCHEMA' | 'TABLE'

export interface ConnectionCandidate {
  id: number
  name: string
  dbType: string
}

export interface SelectedGrantObject {
  key: string
  connectionId: number
  connectionName: string
  dbType: string
  level: GrantObjectLevel
  database?: string
  schema?: string
  table?: string
  /** 展示：连接.库.模式.表 */
  path: string
}

export function isPgStyle(dbType: string) {
  const t = (dbType || '').toLowerCase()
  return t.includes('postgres') || t === 'pg'
}

export function buildObjectKey(item: Omit<SelectedGrantObject, 'key' | 'path'>): string {
  return [item.level, item.connectionId, item.database || '', item.schema || '', item.table || ''].join('|')
}

export function buildObjectPath(item: Omit<SelectedGrantObject, 'key' | 'path'>): string {
  if (item.level === 'CONNECTION') {
    return `${item.connectionName}.*`
  }
  const parts = [item.connectionName]
  if (item.database) parts.push(item.database)
  if (item.level === 'SCHEMA' || item.level === 'TABLE') {
    if (item.schema) parts.push(item.schema)
  }
  if (item.level === 'TABLE' && item.table) parts.push(item.table)
  return parts.join('.')
}

export function toSelectedObject(
  partial: Omit<SelectedGrantObject, 'key' | 'path'>,
): SelectedGrantObject {
  return {
    ...partial,
    key: buildObjectKey(partial),
    path: buildObjectPath(partial),
  }
}

/** B 是否被 A 覆盖（A 为更粗粒度或相等） */
export function covers(parent: SelectedGrantObject, child: SelectedGrantObject): boolean {
  if (parent.connectionId !== child.connectionId) return false
  if (parent.key === child.key) return true
  if (parent.level === 'CONNECTION') return true
  if (parent.level === 'DATABASE') {
    if (parent.database !== child.database) return false
    return child.level === 'SCHEMA' || child.level === 'TABLE' || child.level === 'DATABASE'
  }
  if (parent.level === 'SCHEMA') {
    if (parent.database !== child.database || parent.schema !== child.schema) return false
    return child.level === 'TABLE' || child.level === 'SCHEMA'
  }
  return false
}

function eqIgnore(a?: string | null, b?: string | null) {
  return (a || '').trim().toLowerCase() === (b || '').trim().toLowerCase()
}

export function normalizeAssetScope(scope?: string | null): GrantObjectLevel {
  const s = (scope || '').trim().toUpperCase()
  if (s === 'ALL_TABLES' || s === 'CONNECTION') return 'CONNECTION'
  if (s === 'DATABASE') return 'DATABASE'
  if (s === 'SCHEMA') return 'SCHEMA'
  if (s === 'TABLE' || s === 'SPECIFIC_TABLES') return 'TABLE'
  return 'CONNECTION'
}

export function assetObjectRefs(asset: Pick<WorkspaceAsset, 'objects' | 'tables'>): ObjectRef[] {
  if (asset.objects?.length) return asset.objects
  return asset.tables || []
}

/**
 * 成员授权对象是否落在空间资产范围内（≤ 空间资产）。
 */
export function assetCoversDraft(
  assets: WorkspaceAsset[],
  draft: Omit<SelectedGrantObject, 'key' | 'path'>,
): boolean {
  for (const asset of assets) {
    if (asset.connectionId !== draft.connectionId) continue
    const scope = normalizeAssetScope(asset.objectScope)
    const refs = assetObjectRefs(asset)
    if (scope === 'CONNECTION') {
      return true
    }
    if (scope === 'DATABASE') {
      if (draft.level === 'CONNECTION') continue
      if (refs.some((r) => eqIgnore(r.database, draft.database))) return true
      continue
    }
    if (scope === 'SCHEMA') {
      if (draft.level === 'CONNECTION' || draft.level === 'DATABASE') continue
      if (
        refs.some(
          (r) => eqIgnore(r.database, draft.database) && eqIgnore(r.schema, draft.schema),
        )
      ) {
        return true
      }
      continue
    }
    if (draft.level !== 'TABLE') continue
    if (
      refs.some(
        (r) =>
          eqIgnore(r.database, draft.database) &&
          eqIgnore(r.schema, draft.schema) &&
          eqIgnore(r.name, draft.table),
      )
    ) {
      return true
    }
  }
  return false
}

export function hasConnectionWideAsset(assets: WorkspaceAsset[], connectionId: number) {
  return assets.some(
    (a) => a.connectionId === connectionId && normalizeAssetScope(a.objectScope) === 'CONNECTION',
  )
}

export function hasWideCoverForDatabase(
  assets: WorkspaceAsset[],
  connectionId: number,
  database?: string,
) {
  return assets.some((a) => {
    if (a.connectionId !== connectionId) return false
    const scope = normalizeAssetScope(a.objectScope)
    if (scope === 'CONNECTION') return true
    if (scope === 'DATABASE') {
      return assetObjectRefs(a).some((r) => eqIgnore(r.database, database))
    }
    return false
  })
}

export function hasWideCoverForSchema(
  assets: WorkspaceAsset[],
  connectionId: number,
  database?: string,
  schema?: string,
) {
  if (hasWideCoverForDatabase(assets, connectionId, database)) return true
  return assets.some((a) => {
    if (a.connectionId !== connectionId) return false
    if (normalizeAssetScope(a.objectScope) !== 'SCHEMA') return false
    return assetObjectRefs(a).some(
      (r) => eqIgnore(r.database, database) && eqIgnore(r.schema, schema),
    )
  })
}

/** 从空间资产推导可选库名（非宽范围时，不扫目标库 catalog） */
export function databasesFromAssets(assets: WorkspaceAsset[], connectionId: number): string[] {
  const set = new Set<string>()
  for (const a of assets) {
    if (a.connectionId !== connectionId) continue
    const scope = normalizeAssetScope(a.objectScope)
    if (scope === 'CONNECTION') continue
    for (const r of assetObjectRefs(a)) {
      if (r.database) set.add(r.database)
    }
  }
  return [...set].sort((x, y) => x.localeCompare(y))
}

export function schemasFromAssets(
  assets: WorkspaceAsset[],
  connectionId: number,
  database?: string,
): string[] {
  const set = new Set<string>()
  for (const a of assets) {
    if (a.connectionId !== connectionId) continue
    const scope = normalizeAssetScope(a.objectScope)
    if (scope === 'CONNECTION' || scope === 'DATABASE') continue
    for (const r of assetObjectRefs(a)) {
      if (!eqIgnore(r.database, database)) continue
      if (r.schema) set.add(r.schema)
    }
  }
  return [...set].sort((x, y) => x.localeCompare(y))
}

export function tablesFromAssets(
  assets: WorkspaceAsset[],
  connectionId: number,
  database?: string,
  schema?: string,
): string[] {
  const set = new Set<string>()
  for (const a of assets) {
    if (a.connectionId !== connectionId) continue
    if (normalizeAssetScope(a.objectScope) !== 'TABLE') continue
    for (const r of assetObjectRefs(a)) {
      if (!eqIgnore(r.database, database)) continue
      if (schema && !eqIgnore(r.schema, schema)) continue
      if (r.name) set.add(r.name)
    }
  }
  return [...set].sort((x, y) => x.localeCompare(y))
}

export interface MergeAddResult {
  items: SelectedGrantObject[]
  added: number
  skippedCovered: number
  removedChildren: number
}

/**
 * 添加对象并按包含关系合并：
 * - 已被上级覆盖的不新增
 * - 新增上级时移除被覆盖的下级
 */
export function mergeAddObjects(
  current: SelectedGrantObject[],
  incoming: SelectedGrantObject[],
): MergeAddResult {
  let items = [...current]
  let added = 0
  let skippedCovered = 0
  let removedChildren = 0

  for (const next of incoming) {
    if (items.some((ex) => covers(ex, next))) {
      skippedCovered += 1
      continue
    }
    const before = items.length
    items = items.filter((ex) => !covers(next, ex))
    removedChildren += before - items.length
    if (!items.some((ex) => ex.key === next.key)) {
      items.push(next)
      added += 1
    }
  }

  return { items, added, skippedCovered, removedChildren }
}

/** 转为后端 GrantTarget（按连接 + 层级聚合） */
export function selectedObjectsToTargets(items: SelectedGrantObject[]): GrantTarget[] {
  const byConnLevel = new Map<string, SelectedGrantObject[]>()
  for (const it of items) {
    const k = `${it.connectionId}|${it.level}`
    const list = byConnLevel.get(k) || []
    list.push(it)
    byConnLevel.set(k, list)
  }

  const targets: GrantTarget[] = []
  for (const [, group] of byConnLevel) {
    const first = group[0]
    const scope = first.level as ObjectScopeCode
    if (scope === 'CONNECTION') {
      targets.push({ connectionId: first.connectionId, objectScope: 'CONNECTION' })
      continue
    }
    const objects: ObjectRef[] = group.map((g) => {
      if (scope === 'DATABASE') return { database: g.database }
      if (scope === 'SCHEMA') return { database: g.database, schema: g.schema }
      return { database: g.database, schema: g.schema || undefined, name: g.table }
    })
    targets.push({ connectionId: first.connectionId, objectScope: scope, objects })
  }
  return targets
}

export const LEVEL_LABEL: Record<GrantObjectLevel, string> = {
  CONNECTION: '连接',
  DATABASE: '库',
  SCHEMA: '模式',
  TABLE: '表',
}
