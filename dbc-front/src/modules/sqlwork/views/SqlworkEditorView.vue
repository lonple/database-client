<template>
  <div class="sw">
    <aside class="sw-side">
      <div class="sw-side-hd">
        <div class="ws-row">
          <span class="ws-name" :title="workspaceName">{{ workspaceName || '工作空间' }}</span>
          <a class="switch-link" @click="$router.push('/sqlwork')">切换</a>
        </div>
        <div class="sub">
          <a-select
            :value="active?.connectionId"
            :options="connectionOptions"
            placeholder="选择连接"
            style="width: 100%"
            size="small"
            @update:value="onConnectionChange"
          />
        </div>
      </div>
      <div class="sw-side-body">
        <div v-if="treeLoading" class="tree-loading">加载中…</div>
        <div class="sw-tree">
          <a-empty v-if="!active?.connectionId" description="请选择连接" :image="simpleImage" />
          <a-empty
            v-else-if="!databases.length && !treeLoading"
            description="暂无对象或无权限"
            :image="simpleImage"
          />
          <div v-else-if="databases.length">
            <details
              v-for="db in databases"
              :key="db"
              :open="expandedDbs.has(db)"
              @toggle="(e: Event) => onDbToggle(db, e)"
            >
              <summary>
                <span class="tree-ico tree-ico-db" aria-hidden="true"></span>
                <span class="tree-label">{{ db }}</span>
              </summary>
              <div v-if="expandedDbs.has(db)" class="nest">
                <div v-if="schemaLoading[db]" class="hint-inline">加载 schema…</div>
                <template v-else>
                  <details
                    v-for="schema in schemasByDb[db] || []"
                    :key="`${db}.${schema}`"
                    :open="expandedSchemas.has(`${db}.${schema}`)"
                    @toggle="(e: Event) => onSchemaToggle(db, schema, e)"
                  >
                    <summary>
                      <span class="tree-ico tree-ico-schema" aria-hidden="true"></span>
                      <span class="tree-label">{{ schema }}</span>
                    </summary>
                    <div v-if="expandedSchemas.has(`${db}.${schema}`)" class="nest">
                      <div v-if="tableLoading[`${db}.${schema}`]" class="hint-inline">加载表…</div>
                      <template v-else>
                        <template v-if="(tablesBySchema[`${db}.${schema}`] || []).length">
                          <div
                            v-if="tablesOnly(db, schema).length"
                            class="tree-group"
                          >
                            <div class="tree-group-hd">
                              <span class="tree-ico tree-ico-table" aria-hidden="true"></span>
                              表
                            </div>
                            <div
                              v-for="t in tablesOnly(db, schema)"
                              :key="`t-${t.name}`"
                              class="leaf"
                              :title="t.name"
                              @click="insertTable(schema, t.name)"
                            >
                              <span class="tree-ico tree-ico-table" aria-hidden="true"></span>
                              <span class="tree-label">{{ t.name }}</span>
                            </div>
                          </div>
                          <div
                            v-if="viewsOnly(db, schema).length"
                            class="tree-group"
                          >
                            <div class="tree-group-hd">
                              <span class="tree-ico tree-ico-view" aria-hidden="true"></span>
                              视图
                            </div>
                            <div
                              v-for="t in viewsOnly(db, schema)"
                              :key="`v-${t.name}`"
                              class="leaf"
                              :title="t.name"
                              @click="insertTable(schema, t.name)"
                            >
                              <span class="tree-ico tree-ico-view" aria-hidden="true"></span>
                              <span class="tree-label">{{ t.name }}</span>
                            </div>
                          </div>
                        </template>
                        <div
                          v-else
                          class="hint-inline"
                        >
                          无表或视图
                        </div>
                      </template>
                    </div>
                  </details>
                </template>
              </div>
            </details>
          </div>
        </div>
      </div>
    </aside>
    <main class="sw-main">
      <div class="session-tabs">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-tab"
          :class="{ active: s.id === activeSessionId }"
          @click="switchSession(s.id)"
        >
          <span class="session-title">{{ s.title }}</span>
          <a-tag v-if="s.inTransaction" color="orange" class="tx-tag">事务中</a-tag>
          <button
            type="button"
            class="session-close"
            title="关闭会话"
            @click.stop="closeSession(s.id)"
          >
            ×
          </button>
        </div>
        <button type="button" class="session-add" title="新建会话" @click="addSession">+</button>
      </div>
      <div class="sw-bar">
        <span class="bar-label">库</span>
        <a-select
          :value="active?.selectedDatabase"
          :options="databaseOptions"
          placeholder="选择库"
          style="width: 160px"
          size="middle"
          allow-clear
          @update:value="onDatabaseSelect"
        />
        <span class="bar-label">模式</span>
        <a-select
          :value="active?.selectedSchema"
          :options="schemaOptions"
          placeholder="选择模式"
          style="width: 160px"
          size="middle"
          allow-clear
          :disabled="!active?.selectedDatabase"
          @update:value="(v: string | undefined) => active && (active.selectedSchema = v)"
        />
        <span class="sep" />
        <span class="bar-label">提交</span>
        <a-switch
          :checked="!!active?.manualMode"
          checked-children="手动"
          un-checked-children="自动"
          :disabled="!!active?.inTransaction"
          @update:checked="onManualModeChange"
        />
        <a-button
          :disabled="!canRun || !active?.manualMode || !!active?.inTransaction"
          @click="runTxSql('BEGIN')"
        >
          BEGIN
        </a-button>
        <a-button
          type="primary"
          ghost
          :disabled="!canRun || !active?.inTransaction"
          @click="runTxSql('COMMIT')"
        >
          提交
        </a-button>
        <a-button danger ghost :disabled="!canRun || !active?.inTransaction" @click="runTxSql('ROLLBACK')">
          回滚
        </a-button>
        <span class="sep" />
        <a-button type="primary" :loading="running" :disabled="!canRun" @click="runSql">
          执行
        </a-button>
        <span class="hint">
          <template v-if="active?.manualMode && !active?.inTransaction">
            手动模式：请先执行 BEGIN 开启事务；未开启前语句仍自动提交
          </template>
          <template v-else-if="active?.inTransaction">事务进行中 · 同会话语句走同一连接</template>
          <template v-else>自动提交 · 支持多语句 · 遇错停止</template>
        </span>
      </div>
      <div class="sw-editor-wrap">
        <textarea
          v-if="active"
          v-model="active.sql"
          class="sql-editor"
          spellcheck="false"
          placeholder="可一次提交多条 SQL，例如：&#10;SELECT 1;&#10;SELECT 2;"
        />
        <div class="sw-result">
          <a-tabs
            :activeKey="active?.bottomPanelKey || 'log'"
            size="small"
            class="bottom-tabs"
            @update:activeKey="(k: string | number) => active && (active.bottomPanelKey = String(k))"
          >
            <a-tab-pane key="log" tab="执行日志">
              <div class="sw-result-body">
                <a-table
                  v-if="active?.logs.length"
                  size="small"
                  row-key="key"
                  :columns="logColumns"
                  :data-source="active.logs"
                  :pagination="false"
                  :row-class-name="logRowClass"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'status'">
                      <span :class="severityClass(record)">{{ severityLabel(record) }}</span>
                    </template>
                    <template v-else-if="column.key === 'denyObjects'">
                      <a-tooltip
                        :title="formatDenyObjects(record)"
                        placement="topLeft"
                        overlay-class-name="sqlwork-log-tooltip"
                        :overlay-style="logTooltipStyle"
                      >
                        <span
                          class="cell-ellipsis"
                          :class="{ 'log-error': !record.success && record.denyObjects?.length }"
                        >
                          {{ formatDenyObjects(record) }}
                        </span>
                      </a-tooltip>
                    </template>
                    <template v-else-if="column.key === 'missingOps'">
                      <a-tooltip
                        :title="formatMissingOps(record)"
                        placement="topLeft"
                        overlay-class-name="sqlwork-log-tooltip"
                        :overlay-style="logTooltipStyle"
                      >
                        <span
                          class="cell-ellipsis"
                          :class="{ 'log-error': !record.success && record.missingOps?.length }"
                        >
                          {{ formatMissingOps(record) }}
                        </span>
                      </a-tooltip>
                    </template>
                    <template v-else-if="column.key === 'elapsedMs'">
                      {{ record.elapsedMs ?? 0 }} ms
                    </template>
                    <template v-else-if="column.key === 'detail'">
                      <a-tooltip
                        :title="logDetail(record)"
                        placement="topLeft"
                        overlay-class-name="sqlwork-log-tooltip"
                        :overlay-style="logTooltipStyle"
                      >
                        <span
                          class="cell-ellipsis"
                          :class="{ 'log-warn': isWarn(record), 'log-error': !record.success }"
                        >
                          {{ logDetail(record) }}
                        </span>
                      </a-tooltip>
                    </template>
                  </template>
                </a-table>
                <a-empty v-else description="暂无执行日志" :image="simpleImage" />
              </div>
            </a-tab-pane>
            <a-tab-pane key="result" tab="结果">
              <div class="sw-result-hd">
                <span v-if="active?.lastBatch" class="ok">
                  {{ active.lastBatch.successCount }}/{{ active.lastBatch.totalCount }} 成功
                  <template v-if="active.lastBatch.stoppedOnError"> · 已遇错停止</template>
                  · {{ active.lastBatch.elapsedMs }} ms
                </span>
                <span v-else class="muted">执行结果</span>
                <span v-if="active?.lastBatch?.message" class="muted">{{ active.lastBatch.message }}</span>
              </div>
              <div class="sw-result-body">
                <template v-if="resultStatements.length">
                  <a-tabs
                    :activeKey="active?.activeResultKey || '1'"
                    size="small"
                    class="result-tabs"
                    @update:activeKey="(k: string | number) => active && (active.activeResultKey = String(k))"
                  >
                    <a-tab-pane
                      v-for="stmt in resultStatements"
                      :key="String(stmt.index)"
                      :tab="resultTabLabel(stmt)"
                    >
                      <p v-if="stmt.sqlPreview" class="sql-preview">{{ stmt.sqlPreview }}</p>
                      <a-table
                        size="small"
                        :columns="columnsOf(stmt)"
                        :data-source="rowsOf(stmt)"
                        :pagination="{ pageSize: 50, showSizeChanger: true }"
                        :scroll="{ x: true }"
                      />
                      <p v-if="stmt.truncated" class="muted tip">结果已截断</p>
                    </a-tab-pane>
                  </a-tabs>
                </template>
                <a-empty v-else description="暂无结果集（失败与无权限见执行日志）" :image="simpleImage" />
              </div>
            </a-tab-pane>
          </a-tabs>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import * as sqlworkApi from '@/modules/sqlwork/api/sqlwork'
import type { ExecuteResult, StatementResult, TableItem, WorkbenchSessionInfo } from '@/modules/sqlwork/api/sqlwork'

/** 会话内累积的一条执行日志（与会话 Tab 同生命周期） */
interface ExecLogRow extends StatementResult {
  key: string
  at: string
}

interface SessionState {
  id: string
  title: string
  sql: string
  connectionId?: number
  selectedDatabase?: string
  selectedSchema?: string
  /** 服务端会话 ID */
  serverSessionId?: string
  manualMode: boolean
  inTransaction: boolean
  logs: ExecLogRow[]
  lastBatch: ExecuteResult | null
  bottomPanelKey: string
  activeResultKey: string
  logSeq: number
}

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const route = useRoute()
const workspaceId = computed(() => Number(route.params.id))

const workspaceName = ref('')
const connectionOptions = ref<Array<{ value: number; label: string }>>([])

const databases = ref<string[]>([])
const treeLoading = ref(false)
const expandedDbs = ref(new Set<string>())
const expandedSchemas = ref(new Set<string>())
const schemasByDb = reactive<Record<string, string[]>>({})
const schemaLoading = reactive<Record<string, boolean>>({})
const tablesBySchema = reactive<Record<string, TableItem[]>>({})
const tableLoading = reactive<Record<string, boolean>>({})

const running = ref(false)
let sessionCounter = 1

function createSession(title?: string): SessionState {
  const id = `s-${Date.now()}-${sessionCounter++}`
  return {
    id,
    title: title || `会话 ${sessionCounter - 1}`,
    sql: 'SELECT 1;',
    connectionId: undefined,
    selectedDatabase: undefined,
    selectedSchema: undefined,
    serverSessionId: undefined,
    manualMode: false,
    inTransaction: false,
    logs: [],
    lastBatch: null,
    bottomPanelKey: 'log',
    activeResultKey: '1',
    logSeq: 0,
  }
}

const sessions = ref<SessionState[]>([createSession('会话 1')])
const activeSessionId = ref(sessions.value[0].id)

const active = computed(() => sessions.value.find((s) => s.id === activeSessionId.value) || null)

const canRun = computed(() => !!active.value?.connectionId && !!active.value?.sql?.trim())

const databaseOptions = computed(() => databases.value.map((d) => ({ value: d, label: d })))

function tablesInSchema(db: string, schema: string): TableItem[] {
  return tablesBySchema[`${db}.${schema}`] || []
}

function isView(t: TableItem): boolean {
  return (t.objectType || '').toUpperCase() === 'VIEW'
}

function tablesOnly(db: string, schema: string): TableItem[] {
  return tablesInSchema(db, schema).filter((t) => !isView(t))
}

function viewsOnly(db: string, schema: string): TableItem[] {
  return tablesInSchema(db, schema).filter((t) => isView(t))
}
const schemaOptions = computed(() => {
  const db = active.value?.selectedDatabase
  if (!db) return []
  return (schemasByDb[db] || []).map((s) => ({ value: s, label: s }))
})

const resultStatements = computed(() =>
  (active.value?.lastBatch?.statements || []).filter((s) => s.success && s.columns?.length),
)

const logColumns = [
  { title: '时间', dataIndex: 'at', key: 'at', width: 90 },
  { title: '状态', key: 'status', width: 70 },
  { title: '类型', dataIndex: 'statementType', key: 'statementType', width: 80 },
  { title: '资产对象', key: 'denyObjects', width: 180, ellipsis: true },
  { title: '缺失权限', key: 'missingOps', width: 120, ellipsis: true },
  { title: '失败原因', key: 'detail', ellipsis: true },
  { title: '耗时', key: 'elapsedMs', width: 80 },
]

/** 悬停展示完整失败原因（可换行、可滚动，避免被截断） */
const logTooltipStyle = {
  maxWidth: '560px',
}

function switchSession(id: string) {
  if (id === activeSessionId.value) return
  activeSessionId.value = id
  loadDatabases()
}

async function ensureServerSession(session: SessionState) {
  if (!session.connectionId) {
    throw new Error('请选择连接')
  }
  if (session.serverSessionId) {
    try {
      const resp = await sqlworkApi.updateWorkbenchSession(session.serverSessionId, {
        connectionId: session.connectionId,
        database: session.selectedDatabase,
        schema: session.selectedSchema,
        manualMode: session.manualMode,
      })
      applyServerSession(session, resp.data)
      return
    } catch {
      session.serverSessionId = undefined
      session.inTransaction = false
    }
  }
  const resp = await sqlworkApi.createWorkbenchSession({
    workspaceId: workspaceId.value,
    connectionId: session.connectionId,
    database: session.selectedDatabase,
    schema: session.selectedSchema,
    manualMode: session.manualMode,
  })
  applyServerSession(session, resp.data)
}

function applyServerSession(
  session: SessionState,
  info: WorkbenchSessionInfo | null | undefined,
) {
  if (!info) return
  session.serverSessionId = info.sessionId
  session.manualMode = !!info.manualMode
  session.inTransaction = !!info.inTransaction
}

async function addSession() {
  const s = createSession()
  if (connectionOptions.value.length === 1) {
    s.connectionId = connectionOptions.value[0].value
  } else if (active.value?.connectionId) {
    s.connectionId = active.value.connectionId
  }
  sessions.value.push(s)
  activeSessionId.value = s.id
  if (s.connectionId) {
    try {
      await ensureServerSession(s)
    } catch (e: unknown) {
      message.warning(extractErrorMessage(e) || '创建服务端会话失败')
    }
  }
  loadDatabases()
}

async function closeSession(id: string) {
  if (sessions.value.length <= 1) {
    message.info('至少保留一个会话')
    return
  }
  const idx = sessions.value.findIndex((s) => s.id === id)
  if (idx < 0) return
  const target = sessions.value[idx]
  if (target.serverSessionId) {
    try {
      await sqlworkApi.closeWorkbenchSession(target.serverSessionId)
    } catch {
      // 关闭失败仍移除本地 Tab，避免卡死
    }
  }
  sessions.value.splice(idx, 1)
  if (activeSessionId.value === id) {
    const next = sessions.value[Math.max(0, idx - 1)]
    activeSessionId.value = next.id
    loadDatabases()
  }
}

function appendLogs(session: SessionState, rows: StatementResult[]) {
  const at = new Date().toLocaleTimeString()
  for (const row of rows) {
    session.logSeq += 1
    session.logs.push({
      ...row,
      key: `${session.id}-${session.logSeq}`,
      at,
    })
  }
}

function appendErrorLog(session: SessionState, msg: string, sqlText?: string) {
  session.logSeq += 1
  const preview = (sqlText || session.sql || '').replace(/\s+/g, ' ').trim().slice(0, 200)
  session.logs.push({
    key: `${session.id}-${session.logSeq}`,
    at: new Date().toLocaleTimeString(),
    index: session.logSeq,
    sqlPreview: preview || undefined,
    statementType: 'ERROR',
    columns: [],
    rows: [],
    rowCount: 0,
    truncated: false,
    elapsedMs: 0,
    success: false,
    message: msg,
    severity: 'ERROR',
  })
}

function resultTabLabel(stmt: StatementResult) {
  return `${stmt.index}.${stmt.statementType || '结果'}${stmt.truncated ? '·截断' : ''}`
}

function isWarn(stmt: StatementResult) {
  return stmt.severity === 'WARN' || stmt.globalPolicyAction === 'ALERT'
}

function severityLabel(stmt: StatementResult) {
  if (!stmt.success) return '失败'
  if (isWarn(stmt)) return '告警'
  return '成功'
}

function severityClass(stmt: StatementResult) {
  if (!stmt.success) return 'log-error'
  if (isWarn(stmt)) return 'log-warn'
  return 'log-ok'
}

function logDetail(stmt: StatementResult) {
  if (!stmt.success) {
    if (stmt.message && stmt.message !== 'ok') return stmt.message
    return '执行失败'
  }
  const parts: string[] = []
  if (stmt.sqlPreview) parts.push(stmt.sqlPreview)
  if (stmt.message && stmt.message !== 'ok') parts.push(stmt.message)
  if (stmt.affectedRows != null) parts.push(`影响 ${stmt.affectedRows} 行`)
  if (stmt.columns?.length) {
    parts.push(`${stmt.rowCount} 行${stmt.truncated ? '（截断）' : ''}`)
  }
  return parts.join(' · ') || '-'
}

function formatDenyObjects(stmt: StatementResult) {
  if (stmt.denyObjects?.length) return stmt.denyObjects.join(', ')
  if (stmt.success) return '-'
  return '-'
}

function formatMissingOps(stmt: StatementResult) {
  if (stmt.missingOps?.length) return stmt.missingOps.join(', ')
  return '-'
}

function logRowClass(record: StatementResult) {
  if (!record.success) return 'log-row-error'
  if (isWarn(record)) return 'log-row-warn'
  return ''
}

function columnsOf(stmt: StatementResult) {
  return (stmt.columns || []).map((c, i) => ({
    title: c.name,
    dataIndex: `c${i}`,
    key: `c${i}`,
    ellipsis: true,
  }))
}

function rowsOf(stmt: StatementResult) {
  return (stmt.rows || []).map((row, ri) => {
    const obj: Record<string, unknown> = { key: ri }
    row.forEach((cell, ci) => {
      obj[`c${ci}`] = cell == null ? 'NULL' : String(cell)
    })
    return obj
  })
}

function extractErrorMessage(e: unknown): string {
  if (!e || typeof e !== 'object') return '执行失败'
  const any = e as {
    message?: string
    response?: { data?: { message?: string } }
  }
  return any.response?.data?.message || any.message || '执行失败'
}

function resetTreeState() {
  databases.value = []
  expandedDbs.value = new Set()
  expandedSchemas.value = new Set()
  Object.keys(schemasByDb).forEach((k) => delete schemasByDb[k])
  Object.keys(tablesBySchema).forEach((k) => delete tablesBySchema[k])
}

async function loadDatabases() {
  resetTreeState()
  const connId = active.value?.connectionId
  if (!connId) return
  treeLoading.value = true
  try {
    const resp = await sqlworkApi.fetchDatabases(workspaceId.value, connId)
    databases.value = resp.data || []
  } catch {
    databases.value = []
  } finally {
    treeLoading.value = false
  }
}

async function ensureSchemas(db: string) {
  if (schemasByDb[db] || !active.value?.connectionId) return
  schemaLoading[db] = true
  try {
    const resp = await sqlworkApi.fetchSchemas(workspaceId.value, active.value.connectionId, db)
    schemasByDb[db] = resp.data || []
  } catch {
    schemasByDb[db] = []
  } finally {
    schemaLoading[db] = false
  }
}

async function ensureTables(db: string, schema: string) {
  const key = `${db}.${schema}`
  if (tablesBySchema[key] || !active.value?.connectionId) return
  tableLoading[key] = true
  try {
    const resp = await sqlworkApi.fetchTables(workspaceId.value, active.value.connectionId, {
      database: db,
      schema,
      page: 1,
      size: 100,
    })
    tablesBySchema[key] = resp.data?.items || []
  } catch {
    tablesBySchema[key] = []
  } finally {
    tableLoading[key] = false
  }
}

function onDbToggle(db: string, e: Event) {
  if (!active.value) return
  const open = (e.target as HTMLDetailsElement).open
  const next = new Set(expandedDbs.value)
  if (open) {
    next.add(db)
    expandedDbs.value = next
    ensureSchemas(db)
    active.value.selectedDatabase = db
  } else {
    next.delete(db)
    expandedDbs.value = next
  }
}

function onSchemaToggle(db: string, schema: string, e: Event) {
  if (!active.value) return
  const key = `${db}.${schema}`
  const open = (e.target as HTMLDetailsElement).open
  const next = new Set(expandedSchemas.value)
  if (open) {
    next.add(key)
    expandedSchemas.value = next
    ensureTables(db, schema)
    active.value.selectedDatabase = db
    active.value.selectedSchema = schema
  } else {
    next.delete(key)
    expandedSchemas.value = next
  }
}

async function onDatabaseSelect(v: string | undefined) {
  if (!active.value) return
  if (active.value.inTransaction) {
    message.warning('事务进行中不能切换库，请先提交或回滚')
    return
  }
  active.value.selectedDatabase = v
  active.value.selectedSchema = undefined
  if (v) await ensureSchemas(v)
  if (active.value.serverSessionId && active.value.connectionId) {
    try {
      await ensureServerSession(active.value)
    } catch {
      // ignore
    }
  }
}

async function onConnectionChange(v: number | undefined) {
  if (!active.value) return
  if (active.value.inTransaction) {
    message.warning('事务进行中不能切换连接，请先提交或回滚')
    return
  }
  active.value.connectionId = v
  active.value.selectedDatabase = undefined
  active.value.selectedSchema = undefined
  if (v) {
    try {
      await ensureServerSession(active.value)
    } catch (e: unknown) {
      message.warning(extractErrorMessage(e) || '同步会话失败')
    }
  } else {
    active.value.serverSessionId = undefined
  }
  loadDatabases()
}

async function onManualModeChange(checked: boolean) {
  const session = active.value
  if (!session) return
  if (session.inTransaction && !checked) {
    message.warning('事务进行中不能关闭手动提交')
    return
  }
  session.manualMode = checked
  if (!session.connectionId) {
    message.info(checked ? '已开手动模式，选择连接后执行 BEGIN 开启事务' : '已切回自动提交')
    return
  }
  try {
    await ensureServerSession(session)
    message.info(
      checked
        ? '手动提交：请先执行 BEGIN；未开启前语句仍自动提交'
        : '已切回自动提交',
    )
  } catch (e: unknown) {
    session.manualMode = !checked
    message.error(extractErrorMessage(e))
  }
}

function insertTable(schema: string, name: string) {
  if (!active.value) return
  const ref = schema ? `${schema}.${name}` : name
  const snippet = `SELECT * FROM ${ref} LIMIT 100;`
  active.value.sql = active.value.sql?.trim()
    ? `${active.value.sql.trim()}\n${snippet}`
    : snippet
}

async function runTxSql(sql: string) {
  const session = active.value
  if (!session) return
  const prev = session.sql
  session.sql = sql
  try {
    await runSql()
  } finally {
    session.sql = prev
  }
}

async function runSql() {
  const session = active.value
  if (!session?.connectionId) {
    message.warning('请选择连接')
    return
  }
  running.value = true
  try {
    await ensureServerSession(session)
    const resp = await sqlworkApi.executeSql({
      workspaceId: workspaceId.value,
      connectionId: session.connectionId,
      sql: session.sql,
      database: session.selectedDatabase,
      schema: session.selectedSchema,
      sessionId: session.serverSessionId,
    })
    const batch = resp.data
    session.lastBatch = batch
    if (batch) {
      session.inTransaction = !!batch.inTransaction
      if (batch.manualMode != null) session.manualMode = !!batch.manualMode
    }
    appendLogs(session, batch.statements || [])

    const results = (batch.statements || []).filter((s) => s.success && s.columns?.length)
    const hasAuthOrFail = (batch.statements || []).some((s) => !s.success)
    if (hasAuthOrFail || batch.stoppedOnError || !results.length) {
      session.bottomPanelKey = 'log'
    } else {
      session.bottomPanelKey = 'result'
      session.activeResultKey = String(results[0].index)
    }
    if (batch.stoppedOnError) {
      message.warning(batch.message || '已遇错停止')
    }
  } catch (e: unknown) {
    const msg = extractErrorMessage(e)
    appendErrorLog(session, msg)
    session.lastBatch = null
    session.bottomPanelKey = 'log'
  } finally {
    running.value = false
  }
}

async function loadWorkspace() {
  const wsResp = await sqlworkApi.listMyWorkspaces()
  const ws = (wsResp.data || []).find((w) => w.id === workspaceId.value)
  workspaceName.value = ws?.name || `空间#${workspaceId.value}`
  const connResp = await sqlworkApi.listWorkspaceConnections(workspaceId.value)
  connectionOptions.value = (connResp.data || []).map((c) => ({
    value: c.connectionId,
    label: `${c.name} (${c.dbType})`,
  }))
  if (connectionOptions.value.length === 1 && active.value) {
    active.value.connectionId = connectionOptions.value[0].value
    try {
      await ensureServerSession(active.value)
    } catch {
      // ignore
    }
    await loadDatabases()
  }
}

onMounted(loadWorkspace)

onBeforeUnmount(() => {
  for (const s of sessions.value) {
    if (s.serverSessionId) {
      void sqlworkApi.closeWorkbenchSession(s.serverSessionId).catch(() => undefined)
    }
  }
})
</script>

<style scoped>
.sw {
  display: flex;
  height: calc(100vh - 56px);
  max-height: calc(100vh - 56px);
  overflow: hidden;
  background: #f5f5f5;
}
.sw-side {
  width: 280px;
  flex: 0 0 280px;
  height: 100%;
  max-height: 100%;
  background: #fafafa;
  border-right: 1px solid #f0f0f0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}
.sw-side-hd {
  padding: 12px 14px;
  border-bottom: 1px solid #f0f0f0;
  font-weight: 500;
  background: #fff;
}
.ws-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.ws-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.switch-link {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 400;
}
.sw-side-hd .sub {
  margin-top: 8px;
  font-weight: 400;
}
.sw-side-body {
  min-height: 0;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.tree-loading {
  padding: 12px 14px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.sw-tree {
  padding: 8px 0;
  font-size: 13px;
}
.sw-tree details {
  margin: 0;
}
.sw-tree summary {
  list-style: none;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 4px;
  margin: 1px 6px;
  user-select: none;
}
.sw-tree summary::-webkit-details-marker {
  display: none;
}
.sw-tree summary:hover,
.sw-tree .leaf:hover {
  background: rgba(0, 0, 0, 0.04);
}
.sw-tree .nest {
  padding-left: 14px;
}
.sw-tree .leaf {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 10px 4px 20px;
  margin: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sw-tree .tree-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
.sw-tree .tree-group {
  margin-top: 2px;
}
.sw-tree .tree-group-hd {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px 2px 12px;
  margin: 0 6px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  user-select: none;
}
.sw-tree .tree-ico {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  background-color: #8c8c8c;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}
.sw-tree .tree-ico-db {
  background-color: #1677ff;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cellipse cx='8' cy='4' rx='6' ry='2.2' fill='black'/%3E%3Cpath d='M2 4v8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4' fill='none' stroke='black' stroke-width='1.4'/%3E%3Cpath d='M2 8c0 1.2 2.7 2.2 6 2.2S14 9.2 14 8' fill='none' stroke='black' stroke-width='1.2'/%3E%3C/svg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cellipse cx='8' cy='4' rx='6' ry='2.2' fill='black'/%3E%3Cpath d='M2 4v8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4' fill='none' stroke='black' stroke-width='1.4'/%3E%3Cpath d='M2 8c0 1.2 2.7 2.2 6 2.2S14 9.2 14 8' fill='none' stroke='black' stroke-width='1.2'/%3E%3C/svg%3E");
}
.sw-tree .tree-ico-schema {
  background-color: #fa8c16;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M1.5 4.5h5l1.2 1.2H14.5v7.3H1.5z'/%3E%3C/svg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M1.5 4.5h5l1.2 1.2H14.5v7.3H1.5z'/%3E%3C/svg%3E");
}
.sw-tree .tree-ico-table {
  background-color: #52c41a;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M2 3h12v10H2zm1.2 1.2v2.2h9.6V4.2zm0 3.4v2.2h9.6V7.6zm0 3.4V12h9.6v-1z'/%3E%3C/svg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M2 3h12v10H2zm1.2 1.2v2.2h9.6V4.2zm0 3.4v2.2h9.6V7.6zm0 3.4V12h9.6v-1z'/%3E%3C/svg%3E");
}
.sw-tree .tree-ico-view {
  background-color: #722ed1;
  -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M8 3.2C4.2 3.2 1.3 6.1 1 8c.3 1.9 3.2 4.8 7 4.8s6.7-2.9 7-4.8c-.3-1.9-3.2-4.8-7-4.8zm0 7.1A2.3 2.3 0 1 1 8 5.7a2.3 2.3 0 0 1 0 4.6z'/%3E%3C/svg%3E");
  mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath fill='black' d='M8 3.2C4.2 3.2 1.3 6.1 1 8c.3 1.9 3.2 4.8 7 4.8s6.7-2.9 7-4.8c-.3-1.9-3.2-4.8-7-4.8zm0 7.1A2.3 2.3 0 1 1 8 5.7a2.3 2.3 0 0 1 0 4.6z'/%3E%3C/svg%3E");
}
.sw-tree summary {
  display: flex;
  align-items: center;
}
.hint-inline {
  padding: 4px 10px 4px 28px;
  color: rgba(0, 0, 0, 0.35);
  font-size: 12px;
}
.sw-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
.session-tabs {
  display: flex;
  align-items: stretch;
  gap: 0;
  background: #f0f0f0;
  border-bottom: 1px solid #e8e8e8;
  padding: 0 4px;
  min-height: 36px;
  overflow-x: auto;
}
.session-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px 0 12px;
  height: 36px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  background: transparent;
  border: none;
  border-right: 1px solid #e8e8e8;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}
.session-tab.active {
  background: #fff;
  color: rgba(0, 0, 0, 0.88);
  font-weight: 600;
}
.session-title {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tx-tag {
  margin-inline-end: 0 !important;
  font-size: 11px;
  line-height: 18px;
  padding: 0 4px;
}
.session-close {
  appearance: none;
  border: none;
  background: transparent;
  color: rgba(0, 0, 0, 0.45);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
  border-radius: 2px;
}
.session-close:hover {
  color: rgba(0, 0, 0, 0.88);
  background: rgba(0, 0, 0, 0.06);
}
.session-add {
  appearance: none;
  border: none;
  background: transparent;
  width: 36px;
  height: 36px;
  font-size: 18px;
  color: rgba(0, 0, 0, 0.45);
  cursor: pointer;
  flex-shrink: 0;
}
.session-add:hover {
  color: #1677ff;
  background: rgba(22, 119, 255, 0.06);
}
.sw-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}
.bar-label {
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
}
.sw-bar .sep {
  width: 1px;
  height: 20px;
  background: #d9d9d9;
  margin: 0 4px;
}
.hint {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.sw-editor-wrap {
  flex: 1;
  display: grid;
  grid-template-rows: minmax(160px, 1fr) minmax(200px, 40%);
  min-height: 0;
}
.sql-editor {
  width: 100%;
  height: 100%;
  border: none;
  resize: none;
  padding: 12px 16px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.5;
  outline: none;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}
.sw-result {
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.bottom-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.bottom-tabs :deep(.ant-tabs-nav) {
  margin: 0;
  padding: 0 8px;
  background: #fafafa;
}
.bottom-tabs :deep(.ant-tabs-content-holder) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.bottom-tabs :deep(.ant-tabs-content),
.bottom-tabs :deep(.ant-tabs-tabpane) {
  height: 100%;
}
.sw-result-hd {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  background: #fafafa;
}
.sw-result-hd .ok {
  color: #52c41a;
}
.sw-result-hd .muted,
.muted {
  color: rgba(0, 0, 0, 0.45);
}
.tip {
  margin: 8px 0 0;
  font-size: 12px;
}
.sw-result-body {
  flex: 1;
  overflow: auto;
  padding: 8px;
  height: 100%;
}
.result-tabs {
  height: 100%;
}
.result-tabs :deep(.ant-tabs-content) {
  height: 100%;
}
.sql-preview {
  margin: 0 0 8px;
  padding: 6px 8px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: rgba(0, 0, 0, 0.45);
  background: #fafafa;
  border-radius: 4px;
  word-break: break-all;
}
.log-ok {
  color: #52c41a;
  font-weight: 600;
}
.log-warn {
  color: #cf1322;
  font-weight: 600;
}
.log-error {
  color: #cf1322;
  font-weight: 600;
}
.cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
:deep(.log-row-warn) > td {
  background: #fff2f0;
}
:deep(.log-row-error) > td {
  background: #fff1f0;
}
</style>

<style>
/* Tooltip 挂到 body，需非 scoped；长失败原因换行并可滚动看全 */
.sqlwork-log-tooltip {
  max-width: 560px !important;
}
.sqlwork-log-tooltip .ant-tooltip-inner {
  max-width: 560px;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  text-align: left;
}
</style>
