<template>
  <div class="object-grant-picker">
    <div class="picker-left">
      <div class="picker-left-ops">
        <div class="ops-row">
          <span class="ops-label">授权对象</span>
          <a-radio-group v-model:value="objectLevel" size="small" button-style="solid">
            <a-radio-button value="CONNECTION">连接</a-radio-button>
            <a-radio-button value="DATABASE">库</a-radio-button>
            <a-radio-button value="SCHEMA" :disabled="!anyPgConnection">模式</a-radio-button>
            <a-radio-button value="TABLE">表</a-radio-button>
          </a-radio-group>
        </div>
        <div v-if="objectLevel !== 'CONNECTION'" class="ops-row wrap">
          <a-select
            v-model:value="ctxConnectionId"
            placeholder="选择连接"
            style="min-width: 160px; flex: 1"
            :options="connectionOptions"
            allow-clear
            show-search
            :filter-option="filterOption"
            @change="onCtxConnectionChange"
          />
          <a-select
            v-if="objectLevel === 'SCHEMA' || objectLevel === 'TABLE'"
            v-model:value="ctxDatabase"
            placeholder="选择库"
            style="min-width: 120px; flex: 1"
            :options="databaseOptions"
            :disabled="!ctxConnectionId"
            :loading="loadingDatabases"
            allow-clear
            show-search
            :filter-option="filterOption"
            @change="onCtxDatabaseChange"
          />
          <a-select
            v-if="objectLevel === 'TABLE' && ctxIsPg"
            v-model:value="ctxSchema"
            placeholder="选择模式"
            style="min-width: 110px; flex: 1"
            :options="schemaOptions"
            :disabled="!ctxDatabase"
            :loading="loadingSchemas"
            allow-clear
            show-search
            :filter-option="filterOption"
            @change="onCtxSchemaChange"
          />
        </div>
        <div v-if="objectLevel === 'TABLE'" class="ops-row">
          <a-input-search
            v-model:value="tableKeyword"
            placeholder="搜索表名"
            allow-clear
            size="small"
            style="flex: 1"
            @search="onTableSearch"
          />
        </div>
        <div v-if="objectLevel === 'SCHEMA' && ctxConnectionId && !ctxIsPg" class="hint">
          当前连接无模式层级，请改选「库」或「表」
        </div>
      </div>

      <div class="picker-left-panel">
        <div class="panel-head">
          <span>{{ panelTitle }}</span>
          <a v-if="canLoadPanel" @click="reloadLeft">刷新</a>
        </div>
        <a-alert v-if="panelError" type="error" show-icon :message="panelError" style="margin-bottom: 8px" />
        <a-table
          size="small"
          row-key="key"
          :columns="leftColumns"
          :data-source="leftPageRows"
          :loading="panelLoading"
          :pagination="leftPagination"
          :row-selection="leftSelection"
          :locale="{ emptyText: emptyHint }"
          :scroll="{ y: 240 }"
          @change="onLeftTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              {{ record.label }}
              <span v-if="record.covered" class="hint">（已被上级覆盖）</span>
            </template>
          </template>
        </a-table>
        <div class="panel-foot">
          <span class="hint">已勾选 {{ addableCheckedCount }} 项</span>
          <a-button type="primary" size="small" :disabled="!addableCheckedCount" @click="onAdd">
            添加
          </a-button>
        </div>
      </div>
    </div>

    <div class="picker-right">
      <div class="panel-head">
        <span>已选对象（{{ modelValue.length }}）</span>
        <a-button danger size="small" :disabled="!rightCheckedKeys.length" @click="onBatchRemove">
          批量删除
        </a-button>
      </div>
      <div class="right-filters">
        <a-input v-model:value="filterConn" placeholder="连接" allow-clear size="small" @change="rightPage = 1" />
        <a-input v-model:value="filterDb" placeholder="库" allow-clear size="small" @change="rightPage = 1" />
        <a-input v-model:value="filterSchema" placeholder="模式" allow-clear size="small" @change="rightPage = 1" />
        <a-input v-model:value="filterTable" placeholder="表" allow-clear size="small" @change="rightPage = 1" />
      </div>
      <a-table
        size="small"
        row-key="key"
        :columns="rightColumns"
        :data-source="rightPageRows"
        :pagination="rightPagination"
        :row-selection="rightSelection"
        :locale="{ emptyText: '从左侧勾选后点击「添加」' }"
        :scroll="{ y: 280 }"
        @change="onRightTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'level'">
            <a-tag>{{ levelLabel(record.level) }}</a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a class="danger" @click="removeOne(record.key)">删除</a>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import type { TableProps } from 'ant-design-vue'
import * as metaApi from '@/modules/auth/api/meta'
import type { WorkspaceAsset } from '@/modules/auth/api/workspace'
import {
  LEVEL_LABEL,
  assetCoversDraft,
  covers,
  databasesFromAssets,
  hasConnectionWideAsset,
  hasWideCoverForDatabase,
  hasWideCoverForSchema,
  isPgStyle,
  mergeAddObjects,
  schemasFromAssets,
  tablesFromAssets,
  toSelectedObject,
  type ConnectionCandidate,
  type GrantObjectLevel,
  type SelectedGrantObject,
} from '@/modules/auth/utils/objectGrant'

const props = withDefaults(
  defineProps<{
    workspaceId: number
    connections: ConnectionCandidate[]
    modelValue: SelectedGrantObject[]
    /** 限制候选 ⊆ 空间资产（成员授权）；资产授权配置时不传 */
    workspaceAssets?: WorkspaceAsset[]
    restrictToWorkspaceAssets?: boolean
  }>(),
  {
    workspaceAssets: () => [],
    restrictToWorkspaceAssets: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [SelectedGrantObject[]]
}>()

interface PanelRow {
  key: string
  label: string
  covered: boolean
  draft: Omit<SelectedGrantObject, 'key' | 'path'>
}

const PAGE_SIZE = 10

const objectLevel = ref<GrantObjectLevel>('CONNECTION')
const ctxConnectionId = ref<number | undefined>()
const ctxDatabase = ref<string | undefined>()
const ctxSchema = ref<string | undefined>()
const tableKeyword = ref('')

/** 左侧全量（连接/库/模式客户端分页）；表场景仅当前服务端页 */
const panelRows = ref<PanelRow[]>([])
/** 勾选跨页时缓存 draft */
const draftCache = reactive<Record<string, PanelRow['draft']>>({})
const panelLoading = ref(false)
const panelError = ref('')
const checkedKeys = ref<string[]>([])

const leftPage = ref(1)
const leftPageSize = ref(PAGE_SIZE)
/** 表：服务端 total；其它：等于 panelRows.length */
const leftTotal = ref(0)
const leftServerPaged = computed(() => objectLevel.value === 'TABLE')

const loadingDatabases = ref(false)
const loadingSchemas = ref(false)
const databaseOptions = ref<{ label: string; value: string }[]>([])
const schemaOptions = ref<{ label: string; value: string }[]>([])

const filterConn = ref('')
const filterDb = ref('')
const filterSchema = ref('')
const filterTable = ref('')
const rightCheckedKeys = ref<string[]>([])
const rightPage = ref(1)
const rightPageSize = ref(PAGE_SIZE)

const leftColumns = [{ title: '名称', key: 'name', ellipsis: true }]
const rightColumns = [
  { title: '对象', dataIndex: 'path', key: 'path', ellipsis: true },
  { title: '类型', key: 'level', width: 72 },
  { title: '', key: 'action', width: 56 },
]

const anyPgConnection = computed(() => props.connections.some((c) => isPgStyle(c.dbType)))

const connectionOptions = computed(() =>
  props.connections.map((c) => ({ label: `${c.name}（${c.dbType}）`, value: c.id })),
)

const ctxConnection = computed(() => props.connections.find((c) => c.id === ctxConnectionId.value))

const ctxIsPg = computed(() => (ctxConnection.value ? isPgStyle(ctxConnection.value.dbType) : false))

const canLoadPanel = computed(() => {
  if (objectLevel.value === 'CONNECTION') return props.connections.length > 0
  if (!ctxConnectionId.value) return false
  if (objectLevel.value === 'DATABASE') return true
  if (objectLevel.value === 'SCHEMA') return !!ctxDatabase.value && ctxIsPg.value
  if (objectLevel.value === 'TABLE') {
    if (!ctxDatabase.value) return false
    if (ctxIsPg.value) return !!ctxSchema.value
    return true
  }
  return false
})

const panelTitle = computed(() => {
  if (objectLevel.value === 'CONNECTION') return '可选连接'
  if (objectLevel.value === 'DATABASE') return '可选库'
  if (objectLevel.value === 'SCHEMA') return '可选模式'
  return '可选表'
})

const emptyHint = computed(() => {
  if (props.restrictToWorkspaceAssets && !(props.workspaceAssets || []).length) {
    return '本空间尚无资产授权，请先在「资产授权」中配置'
  }
  if (objectLevel.value === 'CONNECTION') return '暂无候选连接'
  if (!ctxConnectionId.value) return '请先选择连接'
  if (objectLevel.value === 'DATABASE') {
    return props.restrictToWorkspaceAssets
      ? '空间资产中无可用库（整连接资产请选「连接」级别）'
      : '暂无库，可点刷新'
  }
  if (objectLevel.value === 'SCHEMA') {
    if (!ctxDatabase.value) return '请先选择库'
    if (!ctxIsPg.value) return '当前连接无模式'
    return props.restrictToWorkspaceAssets
      ? '空间资产中无可用模式'
      : '暂无模式'
  }
  if (!ctxDatabase.value) return '请先选择库'
  if (ctxIsPg.value && !ctxSchema.value) return '请先选择模式'
  return props.restrictToWorkspaceAssets ? '空间资产中无可用表' : '暂无表'
})

function withinAssets(draft: Omit<SelectedGrantObject, 'key' | 'path'>) {
  if (!props.restrictToWorkspaceAssets) return true
  return assetCoversDraft(props.workspaceAssets || [], draft)
}

const leftPageRows = computed(() => {
  if (leftServerPaged.value) return panelRows.value
  const start = (leftPage.value - 1) * leftPageSize.value
  return panelRows.value.slice(start, start + leftPageSize.value)
})

const leftPagination = computed(() => ({
  current: leftPage.value,
  pageSize: leftPageSize.value,
  total: leftServerPaged.value ? leftTotal.value : panelRows.value.length,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (t: number) => `共 ${t} 条`,
  size: 'small' as const,
}))

const leftSelection = computed<TableProps['rowSelection']>(() => ({
  selectedRowKeys: checkedKeys.value,
  preserveSelectedRowKeys: true,
  getCheckboxProps: (record: PanelRow) => ({ disabled: record.covered }),
  onChange: (keys) => {
    checkedKeys.value = keys.map(String)
  },
}))

const addableCheckedCount = computed(() => {
  let n = 0
  for (const key of checkedKeys.value) {
    const draft = draftCache[key]
    if (!draft) continue
    if (!isCoveredBySelected(draft)) n += 1
  }
  return n
})

const filteredSelected = computed(() => {
  const fc = filterConn.value.trim().toLowerCase()
  const fd = filterDb.value.trim().toLowerCase()
  const fs = filterSchema.value.trim().toLowerCase()
  const ft = filterTable.value.trim().toLowerCase()
  return props.modelValue.filter((it) => {
    if (fc && !it.connectionName.toLowerCase().includes(fc) && !String(it.connectionId).includes(fc)) {
      return false
    }
    if (fd && !(it.database || '').toLowerCase().includes(fd)) return false
    if (fs && !(it.schema || '').toLowerCase().includes(fs)) return false
    if (ft && !(it.table || '').toLowerCase().includes(ft) && !it.path.toLowerCase().includes(ft)) {
      return false
    }
    return true
  })
})

const rightPageRows = computed(() => {
  const start = (rightPage.value - 1) * rightPageSize.value
  return filteredSelected.value.slice(start, start + rightPageSize.value)
})

const rightPagination = computed(() => ({
  current: rightPage.value,
  pageSize: rightPageSize.value,
  total: filteredSelected.value.length,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (t: number) => `共 ${t} 条`,
  size: 'small' as const,
}))

const rightSelection = computed<TableProps['rowSelection']>(() => ({
  selectedRowKeys: rightCheckedKeys.value,
  onChange: (keys) => {
    rightCheckedKeys.value = keys.map(String)
  },
  preserveSelectedRowKeys: true,
}))

function levelLabel(level: GrantObjectLevel) {
  return LEVEL_LABEL[level]
}

function filterOption(input: string, option?: { label?: string }) {
  return (option?.label || '').toLowerCase().includes(input.toLowerCase())
}

function isCoveredBySelected(draft: Omit<SelectedGrantObject, 'key' | 'path'>) {
  const probe = toSelectedObject(draft)
  return props.modelValue.some((ex) => covers(ex, probe))
}

function cacheDrafts(rows: PanelRow[]) {
  for (const row of rows) {
    draftCache[row.key] = row.draft
  }
}

function refreshCoveredFlags() {
  for (const row of panelRows.value) {
    row.covered = isCoveredBySelected(row.draft)
  }
}

async function loadDatabasesForCtx() {
  if (!ctxConnectionId.value) {
    databaseOptions.value = []
    return
  }
  loadingDatabases.value = true
  try {
    const assets = props.workspaceAssets || []
    const connId = ctxConnectionId.value
    if (props.restrictToWorkspaceAssets) {
      if (hasConnectionWideAsset(assets, connId)) {
        const resp = await metaApi.fetchDatabases(props.workspaceId, connId)
        databaseOptions.value = (resp.data || []).map((n) => ({ label: n, value: n }))
      } else {
        databaseOptions.value = databasesFromAssets(assets, connId).map((n) => ({
          label: n,
          value: n,
        }))
      }
    } else {
      const resp = await metaApi.fetchDatabases(props.workspaceId, connId)
      databaseOptions.value = (resp.data || []).map((n) => ({ label: n, value: n }))
    }
  } catch (e: any) {
    databaseOptions.value = []
    message.error(e?.message || '加载库失败')
  } finally {
    loadingDatabases.value = false
  }
}

async function loadSchemasForCtx() {
  if (!ctxConnectionId.value || !ctxDatabase.value || !ctxIsPg.value) {
    schemaOptions.value = []
    return
  }
  loadingSchemas.value = true
  try {
    const assets = props.workspaceAssets || []
    const connId = ctxConnectionId.value
    const db = ctxDatabase.value
    if (props.restrictToWorkspaceAssets) {
      if (hasWideCoverForDatabase(assets, connId, db)) {
        const resp = await metaApi.fetchSchemas(props.workspaceId, connId, db)
        schemaOptions.value = (resp.data || []).map((n) => ({ label: n, value: n }))
      } else {
        schemaOptions.value = schemasFromAssets(assets, connId, db).map((n) => ({
          label: n,
          value: n,
        }))
      }
    } else {
      const resp = await metaApi.fetchSchemas(props.workspaceId, connId, db)
      schemaOptions.value = (resp.data || []).map((n) => ({ label: n, value: n }))
    }
  } catch (e: any) {
    schemaOptions.value = []
    message.error(e?.message || '加载模式失败')
  } finally {
    loadingSchemas.value = false
  }
}

async function loadPanel() {
  panelError.value = ''
  if (!canLoadPanel.value) {
    panelRows.value = []
    leftTotal.value = 0
    return
  }

  panelLoading.value = true
  try {
    const assets = props.workspaceAssets || []

    if (objectLevel.value === 'CONNECTION') {
      const rows = props.connections
        .map((c) => {
          const draft = {
            connectionId: c.id,
            connectionName: c.name,
            dbType: c.dbType,
            level: 'CONNECTION' as const,
          }
          return {
            key: `CONNECTION|${c.id}`,
            label: `${c.name}（整个连接）`,
            covered: isCoveredBySelected(draft),
            draft,
          }
        })
        .filter((row) => withinAssets(row.draft))
      panelRows.value = rows
      leftTotal.value = rows.length
      cacheDrafts(rows)
      return
    }

    const conn = ctxConnection.value
    if (!conn) return

    if (objectLevel.value === 'DATABASE') {
      let names: string[] = []
      if (props.restrictToWorkspaceAssets) {
        if (hasConnectionWideAsset(assets, conn.id)) {
          const resp = await metaApi.fetchDatabases(props.workspaceId, conn.id)
          names = resp.data || []
        } else {
          names = databasesFromAssets(assets, conn.id)
        }
      } else {
        const resp = await metaApi.fetchDatabases(props.workspaceId, conn.id)
        names = resp.data || []
      }
      const rows = names
        .map((db) => {
          const draft = {
            connectionId: conn.id,
            connectionName: conn.name,
            dbType: conn.dbType,
            level: 'DATABASE' as const,
            database: db,
          }
          return {
            key: `DATABASE|${conn.id}|${db}`,
            label: db,
            covered: isCoveredBySelected(draft),
            draft,
          }
        })
        .filter((row) => withinAssets(row.draft))
      panelRows.value = rows
      leftTotal.value = rows.length
      cacheDrafts(rows)
      return
    }

    if (objectLevel.value === 'SCHEMA') {
      let names: string[] = []
      if (props.restrictToWorkspaceAssets) {
        if (hasWideCoverForDatabase(assets, conn.id, ctxDatabase.value)) {
          const resp = await metaApi.fetchSchemas(props.workspaceId, conn.id, ctxDatabase.value)
          names = resp.data || []
        } else {
          names = schemasFromAssets(assets, conn.id, ctxDatabase.value)
        }
      } else {
        const resp = await metaApi.fetchSchemas(props.workspaceId, conn.id, ctxDatabase.value)
        names = resp.data || []
      }
      const rows = names
        .map((sch) => {
          const draft = {
            connectionId: conn.id,
            connectionName: conn.name,
            dbType: conn.dbType,
            level: 'SCHEMA' as const,
            database: ctxDatabase.value,
            schema: sch,
          }
          return {
            key: `SCHEMA|${conn.id}|${ctxDatabase.value}|${sch}`,
            label: sch,
            covered: isCoveredBySelected(draft),
            draft,
          }
        })
        .filter((row) => withinAssets(row.draft))
      panelRows.value = rows
      leftTotal.value = rows.length
      cacheDrafts(rows)
      return
    }

    // TABLE
    if (props.restrictToWorkspaceAssets) {
      const wide = hasWideCoverForSchema(
        assets,
        conn.id,
        ctxDatabase.value,
        ctxIsPg.value ? ctxSchema.value : undefined,
      )
      if (wide) {
        const resp = await metaApi.fetchTables(props.workspaceId, conn.id, {
          database: ctxDatabase.value,
          schema: ctxIsPg.value ? ctxSchema.value : undefined,
          keyword: tableKeyword.value.trim() || undefined,
          page: leftPage.value,
          size: leftPageSize.value,
        })
        const rows = (resp.data?.items || [])
          .map((t) => {
            const draft = {
              connectionId: conn.id,
              connectionName: conn.name,
              dbType: conn.dbType,
              level: 'TABLE' as const,
              database: ctxDatabase.value,
              schema: ctxIsPg.value ? ctxSchema.value : undefined,
              table: t.name,
            }
            return {
              key: `TABLE|${conn.id}|${ctxDatabase.value}|${ctxSchema.value || ''}|${t.name}`,
              label: t.name,
              covered: isCoveredBySelected(draft),
              draft,
            }
          })
          .filter((row) => withinAssets(row.draft))
        panelRows.value = rows
        leftTotal.value = rows.length
        cacheDrafts(rows)
        return
      }
      let names = tablesFromAssets(
        assets,
        conn.id,
        ctxDatabase.value,
        ctxIsPg.value ? ctxSchema.value : undefined,
      )
      const kw = tableKeyword.value.trim().toLowerCase()
      if (kw) {
        names = names.filter((n) => n.toLowerCase().includes(kw))
      }
      leftTotal.value = names.length
      const start = (leftPage.value - 1) * leftPageSize.value
      const pageNames = names.slice(start, start + leftPageSize.value)
      const rows = pageNames.map((name) => {
        const draft = {
          connectionId: conn.id,
          connectionName: conn.name,
          dbType: conn.dbType,
          level: 'TABLE' as const,
          database: ctxDatabase.value,
          schema: ctxIsPg.value ? ctxSchema.value : undefined,
          table: name,
        }
        return {
          key: `TABLE|${conn.id}|${ctxDatabase.value}|${ctxSchema.value || ''}|${name}`,
          label: name,
          covered: isCoveredBySelected(draft),
          draft,
        }
      })
      panelRows.value = rows
      cacheDrafts(rows)
      return
    }

    const resp = await metaApi.fetchTables(props.workspaceId, conn.id, {
      database: ctxDatabase.value,
      schema: ctxIsPg.value ? ctxSchema.value : undefined,
      keyword: tableKeyword.value.trim() || undefined,
      page: leftPage.value,
      size: leftPageSize.value,
    })
    const rows = (resp.data?.items || []).map((t) => {
      const draft = {
        connectionId: conn.id,
        connectionName: conn.name,
        dbType: conn.dbType,
        level: 'TABLE' as const,
        database: ctxDatabase.value,
        schema: ctxIsPg.value ? ctxSchema.value : undefined,
        table: t.name,
      }
      return {
        key: `TABLE|${conn.id}|${ctxDatabase.value}|${ctxSchema.value || ''}|${t.name}`,
        label: t.name,
        covered: isCoveredBySelected(draft),
        draft,
      }
    })
    panelRows.value = rows
    leftTotal.value = resp.data?.total || 0
    cacheDrafts(rows)
  } catch (e: any) {
    panelError.value = e?.message || '加载失败'
    panelRows.value = []
    leftTotal.value = 0
  } finally {
    panelLoading.value = false
  }
}

function reloadLeft() {
  leftPage.value = 1
  checkedKeys.value = []
  void loadPanel()
}

function onLeftTableChange(pag: { current?: number; pageSize?: number }) {
  const nextPage = pag.current || 1
  const nextSize = pag.pageSize || leftPageSize.value
  const sizeChanged = nextSize !== leftPageSize.value
  leftPage.value = sizeChanged ? 1 : nextPage
  leftPageSize.value = nextSize
  if (leftServerPaged.value) {
    void loadPanel()
  }
}

function onRightTableChange(pag: { current?: number; pageSize?: number }) {
  const nextPage = pag.current || 1
  const nextSize = pag.pageSize || rightPageSize.value
  const sizeChanged = nextSize !== rightPageSize.value
  rightPage.value = sizeChanged ? 1 : nextPage
  rightPageSize.value = nextSize
}

function onTableSearch() {
  leftPage.value = 1
  checkedKeys.value = []
  void loadPanel()
}

function onCtxConnectionChange() {
  ctxDatabase.value = undefined
  ctxSchema.value = undefined
  databaseOptions.value = []
  schemaOptions.value = []
  leftPage.value = 1
  checkedKeys.value = []
  if (objectLevel.value !== 'CONNECTION' && ctxConnectionId.value) {
    void loadDatabasesForCtx().then(() => {
      if (objectLevel.value === 'DATABASE') void loadPanel()
      else {
        panelRows.value = []
        leftTotal.value = 0
      }
    })
  } else {
    void loadPanel()
  }
}

function onCtxDatabaseChange() {
  ctxSchema.value = undefined
  schemaOptions.value = []
  leftPage.value = 1
  checkedKeys.value = []
  if (objectLevel.value === 'TABLE' && ctxIsPg.value) {
    void loadSchemasForCtx()
    panelRows.value = []
    leftTotal.value = 0
    return
  }
  if (objectLevel.value === 'SCHEMA' || objectLevel.value === 'TABLE') {
    void loadPanel()
  }
}

function onCtxSchemaChange() {
  leftPage.value = 1
  checkedKeys.value = []
  void loadPanel()
}

function onAdd() {
  const incoming: SelectedGrantObject[] = []
  for (const key of checkedKeys.value) {
    const draft = draftCache[key]
    if (!draft) continue
    if (isCoveredBySelected(draft)) continue
    incoming.push(toSelectedObject(draft))
  }
  if (!incoming.length) {
    message.warning('请勾选可添加的对象')
    return
  }
  const result = mergeAddObjects(props.modelValue, incoming)
  emit('update:modelValue', result.items)
  checkedKeys.value = []
  const tips: string[] = []
  if (result.added) tips.push(`新增 ${result.added} 项`)
  if (result.skippedCovered) tips.push(`${result.skippedCovered} 项已存在或被上级覆盖`)
  if (result.removedChildren) tips.push(`合并移除下级 ${result.removedChildren} 项`)
  message.success(tips.join('，') || '已更新')
  refreshCoveredFlags()
  rightPage.value = 1
}

function removeOne(key: string) {
  emit(
    'update:modelValue',
    props.modelValue.filter((it) => it.key !== key),
  )
  rightCheckedKeys.value = rightCheckedKeys.value.filter((k) => k !== key)
  refreshCoveredFlags()
}

function onBatchRemove() {
  if (!rightCheckedKeys.value.length) return
  const removeSet = new Set(rightCheckedKeys.value)
  emit(
    'update:modelValue',
    props.modelValue.filter((it) => !removeSet.has(it.key)),
  )
  rightCheckedKeys.value = []
  refreshCoveredFlags()
}

watch(objectLevel, (level) => {
  checkedKeys.value = []
  panelRows.value = []
  leftTotal.value = 0
  leftPage.value = 1
  panelError.value = ''
  tableKeyword.value = ''
  if (level === 'CONNECTION') {
    ctxConnectionId.value = undefined
    ctxDatabase.value = undefined
    ctxSchema.value = undefined
    void loadPanel()
    return
  }
  if (level === 'SCHEMA' && ctxConnectionId.value && !ctxIsPg.value) {
    ctxConnectionId.value = undefined
  }
  if (ctxConnectionId.value) {
    void loadDatabasesForCtx().then(() => {
      if (level === 'DATABASE') void loadPanel()
      else if (level === 'SCHEMA' && ctxDatabase.value) void loadPanel()
      else if (level === 'TABLE' && ctxDatabase.value && (!ctxIsPg.value || ctxSchema.value)) {
        void loadPanel()
      }
    })
  }
})

watch(
  () => props.connections,
  () => {
    if (objectLevel.value === 'CONNECTION') void loadPanel()
  },
  { deep: true },
)

watch(
  () => props.modelValue,
  () => {
    refreshCoveredFlags()
    const maxPage = Math.max(1, Math.ceil(filteredSelected.value.length / rightPageSize.value) || 1)
    if (rightPage.value > maxPage) rightPage.value = maxPage
  },
  { deep: true },
)

void loadPanel()
</script>

<style scoped>
.object-grant-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  min-height: 420px;
}
.picker-left,
.picker-right {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.picker-left-ops {
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
  border-radius: 8px 8px 0 0;
}
.ops-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ops-row.wrap {
  flex-wrap: wrap;
}
.ops-row:last-child {
  margin-bottom: 0;
}
.ops-label {
  flex-shrink: 0;
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
}
.picker-left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  min-height: 0;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-weight: 500;
}
.panel-foot {
  margin-top: 8px;
  padding-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f0f0f0;
}
.picker-right {
  padding: 10px 12px;
  background: #fff;
}
.right-filters {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 6px;
  margin-bottom: 8px;
}
.hint {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.danger {
  color: #cf1322;
}
@media (max-width: 900px) {
  .object-grant-picker {
    grid-template-columns: 1fr;
  }
}
</style>
