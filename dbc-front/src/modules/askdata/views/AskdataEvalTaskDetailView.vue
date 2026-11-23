<template>
  <div class="page">
    <div class="hd">
      <div>
        <div class="title-row">
          <h2>{{ task?.name || '任务详情' }}</h2>
          <a-button v-if="task" type="link" size="small" @click="openRename">重命名</a-button>
        </div>
        <div class="sub">
          #{{ taskId }} ·
          <a-tag :color="statusColor(task?.status || '')">{{ task?.status || '-' }}</a-tag>
          · 工作空间 {{ workspaceId }}
        </div>
      </div>
      <a-space>
        <a-button @click="goList">返回列表</a-button>
        <a-button
          v-if="canRun"
          type="primary"
          :loading="starting"
          @click="onRun"
        >
          {{ runButtonLabel }}
        </a-button>
        <a-button
          v-if="task && (task.status === 'RUNNING' || task.status === 'PENDING')"
          danger
          @click="onCancel"
        >
          取消
        </a-button>
        <a-button v-if="task && task.status !== 'RUNNING'" danger @click="onDelete">删除</a-button>
        <a-button @click="load">刷新</a-button>
      </a-space>
    </div>

    <div class="metrics">
      <div v-for="m in metricCards" :key="m.k" class="m-card" :class="m.cls">
        <div class="k">{{ m.k }}</div>
        <div class="v">{{ m.v }}</div>
      </div>
    </div>

    <div class="cat-metrics" v-if="categoryMetrics.length">
      <div class="cat-hd">分类通过率（点击行可筛选用例）</div>
      <a-table
        row-key="category"
        size="small"
        :pagination="false"
        :data-source="categoryMetrics"
        :columns="categoryColumns"
        :custom-row="categoryRowProps"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'category'">
            {{ categoryLabel(record.category) }}
          </template>
          <template v-else-if="column.key === 'passRate'">
            <div class="rate-cell">
              <a-progress
                :percent="record.passRate ?? 0"
                size="small"
                :status="rateStatus(record.passRate)"
              />
              <span class="rate-num">{{ formatRate(record.passRate) }}</span>
            </div>
          </template>
          <template v-else-if="column.key === 'tableSelectRate'">
            <div class="rate-cell">
              <a-progress
                :percent="record.tableSelectRate ?? 0"
                size="small"
                :status="rateStatus(record.tableSelectRate)"
              />
              <span class="rate-num">
                {{ formatRate(record.tableSelectRate) }}
                ({{ record.tableSelectOk ?? 0 }}/{{ record.tableSelectScored ?? 0 }})
              </span>
            </div>
          </template>
        </template>
      </a-table>
    </div>

    <div class="case-toolbar">
      <a-space wrap>
        <span>类型</span>
        <a-select
          v-model:value="filterCategory"
          allow-clear
          placeholder="全部类型"
          style="width: 220px"
          :options="categoryFilterOptions"
          @change="onFilterChange"
        />
        <span v-if="canRun" class="hint">
          已选 {{ selectedCaseIds.length }} 条（可跨页勾选）。点「{{ runButtonLabel }}」即清理对应历史并开跑，无需再确认。
        </span>
        <a-button
          v-if="canRun"
          size="small"
          :disabled="!selectedCaseIds.length"
          @click="clearSelection"
        >
          清空选择
        </a-button>
      </a-space>
    </div>

    <a-table
      row-key="id"
      size="small"
      :loading="loading"
      :data-source="items"
      :columns="columns"
      :row-selection="canRun ? rowSelection : undefined"
      :pagination="{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showTotal: (t: number) => `共 ${t} 条`,
        onChange: onPage,
      }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'category'">
          {{ categoryLabel(record.category) }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="caseStatusColor(record.status)">{{ record.status }}</a-tag>
        </template>
        <template v-else-if="column.key === 'score'">
          {{ record.compareScore == null ? '-' : Number(record.compareScore).toFixed(2) }}
        </template>
        <template v-else-if="column.key === 'tableSelect'">
          <a-tag :color="tableSelectColor(record)">{{ tableSelectLabel(record) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'elapsed'">
          {{ formatElapsed(record.elapsedMs) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button type="link" size="small" @click="openDrawer(record)">明细</a-button>
        </template>
      </template>
    </a-table>

    <a-drawer v-model:open="drawerOpen" width="520" :title="drawer?.caseKey || '用例明细'">
      <template v-if="drawer">
        <h4>问题</h4>
        <pre>{{ drawer.question }}</pre>
        <h4>必须返回字段</h4>
        <div class="req-cols">
          <template v-if="requiredColumnsOf(drawer.compareSpec).length">
            <a-tag v-for="c in requiredColumnsOf(drawer.compareSpec)" :key="c">{{ c }}</a-tag>
          </template>
          <span v-else>-</span>
        </div>
        <h4>期望 SQL</h4>
        <pre>{{ drawer.expectSql || '-' }}</pre>
        <h4 class="sql-hd">
          <span>问数 SQL</span>
          <a-tooltip title="打开画布与大模型执行日志（无工作流时画布为空，仍可查看过程日志）">
            <a-button type="link" size="small" @click="openCanvas">查看详情</a-button>
          </a-tooltip>
        </h4>
        <pre>{{ drawer.askSql || '-' }}</pre>
        <h4>错误</h4>
        <pre>{{ drawer.askError || '-' }}</pre>
        <h4>比对详情</h4>
        <pre>{{ JSON.stringify(drawer.compareDetail || {}, null, 2) }}</pre>
        <div class="kv">
          <div class="k">status</div>
          <div>{{ drawer.status }}</div>
          <div class="k">score</div>
          <div>{{ drawer.compareScore }}</div>
          <div class="k">耗时</div>
          <div>{{ formatElapsed(drawer.elapsedMs) }}</div>
          <div class="k">hitlRounds</div>
          <div>{{ drawer.hitlRounds }}</div>
          <div class="k">traceId</div>
          <div>{{ drawer.traceId }}</div>
          <div class="k">runId</div>
          <div>{{ drawer.runId }}</div>
        </div>
      </template>
    </a-drawer>

    <a-modal
      v-model:open="canvasOpen"
      :title="canvasTitle"
      :footer="null"
      width="92vw"
      :body-style="{ padding: 0 }"
      destroy-on-close
    >
      <AskdataWorkflowCanvasPanel
        v-if="canvasOpen"
        :workflow-id="canvasWorkflowId"
        :run-id="canvasRunId"
        :session-id="canvasSessionId"
        :title="canvasTitle"
        :case-error="canvasCaseError"
      />
    </a-modal>

    <a-modal
      v-model:open="renameOpen"
      title="修改任务名称"
      ok-text="保存"
      :confirm-loading="renameSaving"
      @ok="onRenameOk"
    >
      <a-input
        v-model:value="renameName"
        :maxlength="128"
        allow-clear
        placeholder="请输入任务名称"
        @pressEnter="onRenameOk"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import * as evalApi from '@/modules/askdata/api/eval'
import type { EvalCategoryMetric, EvalTask, EvalTaskCase } from '@/modules/askdata/api/eval'
import AskdataWorkflowCanvasPanel from '@/modules/askdata/components/AskdataWorkflowCanvasPanel.vue'

const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => Number(route.params.workspaceId))
const taskId = computed(() => Number(route.params.taskId))

const loading = ref(false)
const task = ref<EvalTask | null>(null)
const items = ref<EvalTaskCase[]>([])
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const filterCategory = ref<string | undefined>(undefined)
const drawerOpen = ref(false)
const drawer = ref<EvalTaskCase | null>(null)
const selectedCaseIds = ref<number[]>([])
const starting = ref(false)
const canvasOpen = ref(false)
const canvasWorkflowId = ref<number | null>(null)
const canvasRunId = ref<number | null>(null)
const canvasSessionId = ref<number | null>(null)
const canvasTitle = ref('工作流详情')
const canvasCaseError = ref<string | null>(null)
const renameOpen = ref(false)
const renameName = ref('')
const renameSaving = ref(false)
let timer: number | undefined
let refreshing = false

const canRun = computed(() => {
  const s = task.value?.status
  return s === 'PENDING' || s === 'SUCCEEDED' || s === 'FAILED' || s === 'CANCELLED'
})

const runButtonLabel = computed(() =>
  task.value?.status === 'PENDING' ? '启动跑批' : '重新执行',
)

function applyCaseSelection(
  next: Set<number>,
  records: { id: number }[],
  selected: boolean,
) {
  for (const r of records) {
    const id = Number(r.id)
    if (Number.isNaN(id)) continue
    if (selected) next.add(id)
    else next.delete(id)
  }
}

const rowSelection = computed(() => ({
  selectedRowKeys: selectedCaseIds.value,
  preserveSelectedRowKeys: true,
  onSelect(record: EvalTaskCase, selected: boolean) {
    const next = new Set(selectedCaseIds.value)
    applyCaseSelection(next, [record], selected)
    selectedCaseIds.value = [...next]
  },
  onSelectAll(selected: boolean, _rows: EvalTaskCase[], changeRows: EvalTaskCase[]) {
    const next = new Set(selectedCaseIds.value)
    applyCaseSelection(next, changeRows || [], selected)
    selectedCaseIds.value = [...next]
  },
}))

const columns = [
  { title: 'case_key', dataIndex: 'caseKey', key: 'caseKey', width: 150 },
  { title: '类型', key: 'category', width: 160 },
  { title: '状态', key: 'status', width: 130 },
  { title: '分数', key: 'score', width: 80 },
  { title: '选表', key: 'tableSelect', width: 70 },
  { title: '耗时', key: 'elapsed', width: 90 },
  { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
  { title: 'ask行', dataIndex: 'askRowCount', key: 'askRowCount', width: 70 },
  { title: '操作', key: 'action', width: 80 },
]

function tableSelectOf(record: EvalTaskCase) {
  const ts = record.compareDetail?.tableSelect
  return ts && typeof ts === 'object' ? (ts as Record<string, unknown>) : null
}

function tableSelectLabel(record: EvalTaskCase) {
  const ts = tableSelectOf(record)
  if (!ts || ts.scored !== true) return '-'
  return ts.ok === true ? '✓' : '✗'
}

function tableSelectColor(record: EvalTaskCase) {
  const ts = tableSelectOf(record)
  if (!ts || ts.scored !== true) return 'default'
  return ts.ok === true ? 'green' : 'red'
}

function formatElapsed(ms?: number | null) {
  if (ms == null || Number.isNaN(ms)) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s % 60)
  return `${m}m ${String(rem).padStart(2, '0')}s`
}

function requiredColumnsOf(spec?: Record<string, unknown> | null): string[] {
  if (!spec) return []
  const raw = spec.requiredColumns ?? spec.required_columns ?? spec.columns
  if (!Array.isArray(raw)) return []
  return raw.map((c) => String(c)).filter(Boolean)
}

const metricCards = computed(() => {
  const m = task.value?.metrics || {}
  const wall = task.value?.elapsedMs ?? m.elapsedMs
  return [
    { k: '总数', v: m.total ?? 0, cls: '' },
    { k: '通过率', v: formatRate(m.passRate), cls: rateCardClass(m.passRate) },
    { k: '通过', v: m.passed ?? 0, cls: 'ok' },
    { k: '精确通过', v: m.exactPass ?? 0, cls: 'ok' },
    { k: '选表正确率', v: formatRate(m.tableSelectRate as number | null | undefined), cls: rateCardClass(m.tableSelectRate as number | null | undefined) },
    { k: '选表正确', v: `${m.tableSelectOk ?? 0}/${m.tableSelectScored ?? 0}`, cls: 'ok' },
    { k: '≥80%', v: m.partialGe80 ?? 0, cls: '' },
    { k: '问数失败', v: m.askFailed ?? 0, cls: 'warn' },
    { k: '拒答正确', v: m.refuseOk ?? 0, cls: '' },
    { k: '误出数', v: m.refuseBadLeak ?? 0, cls: 'warn' },
    { k: 'HITL补全通过', v: m.hitlSupplementPass ?? 0, cls: '' },
    { k: 'BOARD通过', v: m.boardPass ?? 0, cls: 'ok' },
    { k: '任务耗时', v: formatElapsed(wall as number | null | undefined), cls: '' },
    { k: '用例耗时合计', v: formatElapsed(m.elapsedMsSum as number | null | undefined), cls: '' },
    { k: '用例平均耗时', v: formatElapsed(m.elapsedMsAvg as number | null | undefined), cls: '' },
  ]
})

const CATEGORY_LABELS: Record<string, string> = {
  SINGLE_FILTER: '单表过滤',
  MULTI_JOIN_FILTER: '多表关联过滤',
  SINGLE_AGG: '单表聚合',
  MULTI_JOIN_AGG: '多表关联聚合',
  MULTI_GOVERN_FILTER: '治理过滤',
  MULTI_GOVERN_AGG: '治理聚合',
}

const categoryColumns = [
  { title: '分类', key: 'category', width: 200 },
  { title: '用例数', dataIndex: 'total', key: 'total', width: 90 },
  { title: '通过', dataIndex: 'passed', key: 'passed', width: 90 },
  { title: '精确通过', dataIndex: 'exactPass', key: 'exactPass', width: 100 },
  { title: '拒答正确', dataIndex: 'refuseOk', key: 'refuseOk', width: 100 },
  { title: '问数失败', dataIndex: 'askFailed', key: 'askFailed', width: 100 },
  { title: '通过率', key: 'passRate', width: 160 },
  { title: '选表正确率', key: 'tableSelectRate', width: 200 },
]

const categoryMetrics = computed<EvalCategoryMetric[]>(
  () => task.value?.metrics?.byCategory || [],
)

const categoryFilterOptions = computed(() => {
  const fromMetrics = categoryMetrics.value
    .map((m) => (m.category || '').trim())
    .filter(Boolean)
  const codes = fromMetrics.length ? fromMetrics : Object.keys(CATEGORY_LABELS)
  const uniq = [...new Set(codes)]
  return uniq.map((code) => ({
    value: code,
    label: CATEGORY_LABELS[code] ? `${CATEGORY_LABELS[code]}（${code}）` : code,
  }))
})

function categoryLabel(code?: string | null) {
  const c = (code || '').trim() || '未知'
  return CATEGORY_LABELS[c] ? `${CATEGORY_LABELS[c]}（${c}）` : c
}

function formatRate(rate?: number | null) {
  if (rate == null || Number.isNaN(rate)) return '-'
  return `${Number(rate).toFixed(1)}%`
}

function rateStatus(rate?: number | null): 'success' | 'normal' | 'exception' {
  if (rate == null) return 'normal'
  if (rate >= 80) return 'success'
  if (rate < 50) return 'exception'
  return 'normal'
}

function rateCardClass(rate?: number | null) {
  if (rate == null) return ''
  if (rate >= 80) return 'ok'
  if (rate < 50) return 'warn'
  return ''
}

function statusColor(s: string) {
  if (s === 'SUCCEEDED') return 'green'
  if (s === 'RUNNING') return 'blue'
  if (s === 'FAILED') return 'red'
  if (s === 'CANCELLED') return 'orange'
  return 'default'
}

function caseStatusColor(s: string) {
  if (s === 'PASSED' || s === 'REFUSED_OK') return 'green'
  if (s === 'PARTIAL_GE_80') return 'blue'
  if (s === 'RUNNING') return 'processing'
  if (
    s === 'REFUSED_BAD' ||
    s === 'ASK_FAILED' ||
    s === 'FAILED_COMPARE' ||
    s === 'MISSING_REQUIRED'
  )
    return 'red'
  return 'default'
}

function applyPayload(resp: Awaited<ReturnType<typeof evalApi.listEvalTaskCases>>) {
  items.value = resp.data?.items || []
  total.value = resp.data?.total || 0
  task.value = resp.data?.task || null
  if (drawer.value) {
    const updated = items.value.find((i) => i.id === drawer.value!.id)
    if (updated) drawer.value = updated
  }
}

/** 首次进入 / 手动刷新：带 loading */
async function load() {
  loading.value = true
  try {
    const resp = await evalApi.listEvalTaskCases(taskId.value, {
      page: page.value,
      pageSize: pageSize.value,
      category: filterCategory.value || undefined,
    })
    applyPayload(resp)
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

/** 跑批中轮询：只合并状态，不触发表格 loading / 整页闪烁 */
async function refreshStatus() {
  if (refreshing || loading.value) return
  if (task.value?.status !== 'RUNNING') return
  refreshing = true
  try {
    const resp = await evalApi.listEvalTaskCases(taskId.value, {
      page: page.value,
      pageSize: pageSize.value,
      category: filterCategory.value || undefined,
    })
    applyPayload(resp)
  } catch {
    /* 静默刷新失败不打断页面 */
  } finally {
    refreshing = false
  }
}

function onPage(p: number, ps: number) {
  page.value = p
  pageSize.value = ps
  void load()
}

function onFilterChange() {
  page.value = 1
  void load()
}

function categoryRowProps(record: EvalCategoryMetric) {
  const code = (record.category || '').trim()
  const active = !!code && filterCategory.value === code
  return {
    style: {
      cursor: code ? 'pointer' : 'default',
      background: active ? '#e6f4ff' : undefined,
    },
    onClick: () => {
      if (!code) return
      filterCategory.value = filterCategory.value === code ? undefined : code
      onFilterChange()
    },
  }
}

function openDrawer(row: EvalTaskCase) {
  drawer.value = row
  drawerOpen.value = true
}

function openCanvas() {
  const row = drawer.value
  if (!row) return
  canvasWorkflowId.value = row.workflowId ?? null
  canvasRunId.value = row.runId ?? null
  canvasSessionId.value = row.sessionId ?? null
  canvasCaseError.value = row.askError || null
  canvasTitle.value = row.workflowId
    ? `用例 ${row.caseKey} · 工作流`
    : `用例 ${row.caseKey} · 过程详情`
  canvasOpen.value = true
}

function clearSelection() {
  selectedCaseIds.value = []
}

function openRename() {
  if (!task.value) return
  renameName.value = task.value.name || ''
  renameOpen.value = true
}

async function onRenameOk() {
  const name = renameName.value.trim()
  if (!name) {
    message.warning('任务名称不能为空')
    return Promise.reject()
  }
  if (name === task.value?.name) {
    renameOpen.value = false
    return
  }
  renameSaving.value = true
  try {
    const resp = await evalApi.patchEvalTask(taskId.value, { name })
    if (resp.data) {
      task.value = { ...task.value!, ...resp.data }
    } else if (task.value) {
      task.value = { ...task.value, name }
    }
    message.success('任务名称已更新')
    renameOpen.value = false
  } catch (e: any) {
    message.error(e?.message || '修改失败')
    return Promise.reject(e)
  } finally {
    renameSaving.value = false
  }
}

async function onRun() {
  if (!task.value || starting.value) return
  const ids = [...selectedCaseIds.value].map((x) => Number(x)).filter((x) => !Number.isNaN(x))
  const partial = ids.length > 0
  starting.value = true
  try {
    await evalApi.startEvalTask(
      taskId.value,
      partial ? { taskCaseIds: ids } : undefined,
    )
    message.success(partial ? `已启动（${ids.length} 条）` : '已启动（全部）')
    selectedCaseIds.value = []
    page.value = 1
    await load()
    // 后台协程置 RUNNING 有极短窗口；再刷一次避免界面停在 PENDING
    window.setTimeout(() => void load(), 600)
  } catch (e: any) {
    message.error(e?.message || '启动失败')
  } finally {
    starting.value = false
  }
}

async function onCancel() {
  try {
    await evalApi.cancelEvalTask(taskId.value)
    message.success('已请求取消')
    await load()
  } catch (e: any) {
    message.error(e?.message || '取消失败')
  }
}

function onDelete() {
  if (!task.value) return
  Modal.confirm({
    title: '删除测评任务',
    content: `确认删除「${task.value.name}」？用例跑批记录将一并删除。`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await evalApi.deleteEvalTask(taskId.value)
        message.success('已删除')
        goList()
      } catch (e: any) {
        message.error(e?.message || '删除失败')
        throw e
      }
    },
  })
}

function goList() {
  router.push({
    name: 'askdata-eval-tasks',
    params: { workspaceId: String(workspaceId.value) },
    query: task.value ? { projectId: String(task.value.projectId) } : {},
  })
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => {
    // 仅跑批中轮询；PENDING（未启动）不刷
    if (task.value?.status === 'RUNNING') {
      void refreshStatus()
    }
  }, 3000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.page {
  padding: 16px 20px;
  height: 100%;
  overflow: auto;
  background: #f5f5f5;
}
.hd {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 4px;
}
.hd h2 {
  margin: 0;
  font-size: 18px;
}
.sub {
  margin-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.case-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px 8px 0 0;
}
.case-toolbar .hint {
  font-size: 12px;
  color: #8c8c8c;
}
.m-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px 14px;
}
.m-card .k {
  font-size: 12px;
  color: #8c8c8c;
}
.m-card .v {
  margin-top: 4px;
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  word-break: break-all;
}
.m-card.warn .v {
  color: #cf1322;
}
.m-card.ok .v {
  color: #389e0d;
}
.cat-metrics {
  margin-bottom: 14px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 10px 12px 4px;
}
.cat-hd {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.rate-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 280px;
}
.rate-num {
  flex: 0 0 56px;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}
pre {
  margin: 0 0 12px;
  padding: 10px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 12px;
}
h4 {
  margin: 12px 0 6px;
  font-size: 13px;
}
.sql-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.req-cols {
  margin: 0 0 12px;
  min-height: 24px;
}
.kv {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 6px 10px;
  font-size: 13px;
}
.kv .k {
  color: #8c8c8c;
}
</style>
