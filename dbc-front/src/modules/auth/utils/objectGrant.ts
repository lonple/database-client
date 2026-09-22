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

/** 单条空间资产是否覆盖草稿对象。 */
function assetCoversDraftOne(
  asset: WorkspaceAsset,
  draft: Omit<SelectedGrantObject, 'key' | 'path'>,
): boolean {
  if (asset.connectionId !== draft.connectionId) return false
  const scope = normalizeAssetScope(asset.objectScope)
  const refs = assetObjectRefs(asset)
  if (scope === 'CONNECTION') {
    return true
  }
  if (scope === 'DATABASE') {
    if (draft.level === 'CONNECTION') return false
    return refs.some((r) => eqIgnore(r.database, draft.database))
  }
  if (scope === 'SCHEMA') {
    if (draft.level === 'CONNECTION' || draft.level === 'DATABASE') return false
    return refs.some(
      (r) => eqIgnore(r.database, draft.database) && eqIgnore(r.schema, draft.schema),
    )
  }
  if (draft.level !== 'TABLE') return false
  return refs.some(
    (r) =>
      eqIgnore(r.database, draft.database) &&
      eqIgnore(r.schema, draft.schema) &&
      eqIgnore(r.name, draft.table),
  )
}

/**
 * 成员授权对象是否落在空间资产范围内（≤ 空间资产）。
 */
export function assetCoversDraft(
  assets: WorkspaceAsset[],
  draft: Omit<SelectedGrantObject, 'key' | 'path'>,
): boolean {
  return assets.some((asset) => assetCoversDraftOne(asset, draft))
}

function normalizeOpsList(ops?: string[] | null): string[] {
  if (!ops?.length) return []
  const set = new Set(ops.map((o) => String(o).toUpperCase()))
  return [...set]
}

/**
 * 单个草稿对象在空间资产下可授予的 SQL 权限（覆盖资产 ops 并集）。
 */
export function allowedOpsForDraft(
  assets: WorkspaceAsset[],
  draft: Omit<SelectedGrantObject, 'key' | 'path'>,
): string[] {
  const set = new Set<string>()
  for (const asset of assets) {
    if (!assetCoversDraftOne(asset, draft)) continue
    for (const op of normalizeOpsList(asset.ops)) {
      set.add(op)
    }
  }
  return [...set]
}

/**
 * 多选对象时，向导共用一份 ops：取各对象允许权限的交集（再与产品全量对齐由调用方处理）。
 */
export function allowedOpsForSelection(
  assets: WorkspaceAsset[],
  selected: Array<Omit<SelectedGrantObject, 'key' | 'path'> | SelectedGrantObject>,
): string[] {
  if (!selected.length) return []
  let intersection: Set<string> | null = null
  for (const draft of selected) {
    const allowed = new Set(allowedOpsForDraft(assets, draft))
    if (intersection == null) {
      intersection = allowed
      continue
    }
    for (const op of [...intersection]) {
      if (!allowed.has(op)) intersection.delete(op)
    }
  }
  return intersection ? [...intersection] : []
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

/**
 * 将已有资产/成员授权记录还原为选中对象列表（编辑回填）。
 */
export function grantRecordToSelectedObjects(input: {
  connectionId: number
  connectionName?: string | null
  objectScope?: string | null
  objects?: ObjectRef[]
  tables?: ObjectRef[]
  dbType?: string
}): SelectedGrantObject[] {
  const level = normalizeAssetScope(input.objectScope)
  const connectionName = input.connectionName || `连接#${input.connectionId}`
  const dbType = input.dbType || 'postgresql'
  if (level === 'CONNECTION') {
    return [
      toSelectedObject({
        connectionId: input.connectionId,
        connectionName,
        dbType,
        level: 'CONNECTION',
      }),
    ]
  }
  const refs = assetObjectRefs({ objects: input.objects, tables: input.tables })
  if (!refs.length) return []
  return refs.map((r) =>
    toSelectedObject({
      connectionId: input.connectionId,
      connectionName,
      dbType,
      level,
      database: r.database,
      schema: r.schema,
      table: r.name,
    }),
  )
}

export const LEVEL_LABEL: Record<GrantObjectLevel, string> = {
  CONNECTION: '连接',
  DATABASE: '库',
  SCHEMA: '模式',
  TABLE: '表',
}
