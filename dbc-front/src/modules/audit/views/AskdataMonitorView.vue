<template>
  <div class="page">
    <div class="hd">
      <h2>智能问数监控</h2>
      <a-space>
        <a-select v-model:value="hours" style="width: 120px" :options="hourOptions" @change="loadSummary" />
        <a-button @click="reload">刷新</a-button>
      </a-space>
    </div>

    <a-row :gutter="12" class="summary">
      <a-col :span="6" v-for="b in summaryBuckets" :key="b.kind + b.status">
        <a-card size="small">
          <div class="card-k">{{ b.kind }} / {{ b.status }}</div>
          <div class="card-v">{{ b.count }}</div>
          <div class="card-s">均延迟 {{ Math.round(b.avgLatencyMs) }} ms</div>
        </a-card>
      </a-col>
    </a-row>

    <a-card size="small">
      <template #title>
        <div class="card-title">
          <template v-if="view === 'turns'">问数列表</template>
          <template v-else>
            <a-button type="link" class="back-btn" @click="backToTurns">返回列表</a-button>
            <span>问数详情 · Span</span>
            <span v-if="activeTurn" class="turn-q" :title="activeTurn.question">
              {{ activeTurn.question }}
            </span>
          </template>
        </div>
      </template>

      <template v-if="view === 'turns'">
        <a-form layout="inline" class="filters">
          <a-form-item label="状态">
            <a-select
              v-model:value="turnFilters.status"
              allow-clear
              style="width: 140px"
              :options="turnStatusOptions"
            />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" @click="loadTurns">查询</a-button>
          </a-form-item>
        </a-form>
        <a-table
          row-key="id"
          size="middle"
          :loading="loading"
          :columns="turnColumns"
          :data-source="turnItems"
          :pagination="turnPagination"
          @change="onTurnTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'question'">
              <span class="q-cell" :title="record.question">{{ record.question }}</span>
            </template>
            <template v-else-if="column.key === 'latencyMs'">
              {{ record.latencyMs != null ? record.latencyMs : '—' }}
            </template>
            <template v-else-if="column.key === 'tokenTotal'">
              {{ record.tokenTotal != null ? record.tokenTotal : '—' }}
            </template>
            <template v-else-if="column.key === 'finishedAt'">
              {{ record.finishedAt || '—' }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="openTurnDetail(record)">详情</a-button>
            </template>
          </template>
        </a-table>
      </template>

      <template v-else>
        <a-form layout="inline" class="filters">
          <a-form-item label="类型">
            <a-select v-model:value="spanFilters.kind" allow-clear style="width: 120px" :options="kindOptions" />
          </a-form-item>
          <a-form-item label="状态">
            <a-select
              v-model:value="spanFilters.status"
              allow-clear
              style="width: 120px"
              :options="statusOptions"
            />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" @click="loadSpans">查询</a-button>
          </a-form-item>
        </a-form>
        <a-table
          row-key="id"
          size="middle"
          :loading="loading"
          :columns="spanColumns"
          :data-source="spanItems"
          :pagination="spanPagination"
          @change="onSpanTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'latencyMs'">
              {{ record.latencyMs != null ? record.latencyMs : '—' }}
            </template>
            <template v-else-if="column.key === 'tokenIn'">
              {{ record.kind === 'LLM' && record.tokenIn != null ? record.tokenIn : '—' }}
            </template>
            <template v-else-if="column.key === 'tokenOut'">
              {{ record.kind === 'LLM' && record.tokenOut != null ? record.tokenOut : '—' }}
            </template>
            <template v-else-if="column.key === 'model'">
              {{ record.kind === 'LLM' && record.model ? record.model : '—' }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="openSpanDetail(record.id)">详情</a-button>
            </template>
          </template>
        </a-table>
      </template>
    </a-card>

    <a-drawer
      v-model:open="detailOpen"
      title="Span 详情"
      :width="detailDrawerWidth"
      root-class-name="ask-span-detail-drawer"
      destroy-on-close
    >
      <template v-if="detailData">
        <a-descriptions size="small" :column="2" bordered class="meta-desc">
          <a-descriptions-item label="编号">{{ detailData.id }}</a-descriptions-item>
          <a-descriptions-item label="类型">{{ detailData.kind }}</a-descriptions-item>
          <a-descriptions-item label="环节">{{ detailData.name }}</a-descriptions-item>
          <a-descriptions-item label="状态">{{ detailData.status }}</a-descriptions-item>
          <a-descriptions-item label="模型">{{ detailData.model || '—' }}</a-descriptions-item>
          <a-descriptions-item label="耗时">
            {{ detailData.latencyMs != null ? detailData.latencyMs + ' ms' : '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="Token">
            in {{ detailData.tokenIn ?? '—' }} / out {{ detailData.tokenOut ?? '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="轮次">{{ detailData.llmRoundCount ?? 0 }}</a-descriptions-item>
        </a-descriptions>

        <template v-if="detailRounds.length">
          <div class="rounds-hd">与大模型交互（共 {{ detailRounds.length }} 轮）</div>
          <a-collapse v-model:activeKey="roundActiveKeys">
            <a-collapse-panel
              v-for="(round, idx) in detailRounds"
              :key="String(idx)"
              :header="roundPanelTitle(round, idx)"
            >
              <div class="round-block">
                <div class="round-label">提示词（发送）</div>
                <pre class="detail">{{ formatMessages(round.prompt) }}</pre>
              </div>
              <div class="round-block">
                <div class="round-label">返回（模型）</div>
                <pre class="detail">{{ formatResponse(round.response) }}</pre>
              </div>
              <div v-if="round.note" class="round-note">{{ round.note }}</div>
            </a-collapse-panel>
          </a-collapse>
        </template>
        <a-empty v-else description="本 Span 无 LLM 提示词/返回记录" />

        <div class="raw-hd">原始 payloadMeta</div>
        <pre class="detail muted">{{ detailPayloadJson }}</pre>
      </template>
    </a-drawer>

    <Teleport to="body">
      <div
        v-if="detailOpen"
        class="ask-span-drawer-resize-handle"
        :class="{ dragging: drawerResizing }"
        :style="{ right: detailDrawerWidth + 'px' }"
        title="拖动调整宽度"
        @pointerdown.prevent="onDrawerResizeStart"
      />
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as askApi from '@/modules/askdata/api/askdata'

const DRAWER_WIDTH_KEY = 'askdata.spanDetailDrawerWidth'
const DRAWER_WIDTH_MIN = 420
const DRAWER_WIDTH_DEFAULT = 720

function loadDrawerWidth(): number {
  try {
    const raw = sessionStorage.getItem(DRAWER_WIDTH_KEY)
    const n = raw ? Number(raw) : NaN
    if (Number.isFinite(n) && n >= DRAWER_WIDTH_MIN) return Math.floor(n)
  } catch {
    /* ignore */
  }
  return DRAWER_WIDTH_DEFAULT
}

function clampDrawerWidth(w: number): number {
  const max = Math.max(DRAWER_WIDTH_MIN, Math.floor(window.innerWidth * 0.92))
  return Math.min(max, Math.max(DRAWER_WIDTH_MIN, Math.floor(w)))
}

type LlmRound = {
  step?: number
  role?: string
  prompt?: unknown
  response?: unknown
  note?: string
  childSpanId?: number
}

const hours = ref(24)
const hourOptions = [
  { label: '近 24 小时', value: 24 },
  { label: '近 72 小时', value: 72 },
  { label: '近 7 天', value: 168 },
]
const kindOptions = [
  { label: 'LLM', value: 'LLM' },
  { label: 'GRAPH', value: 'GRAPH' },
  { label: 'TOOL', value: 'TOOL' },
  { label: 'HITL', value: 'HITL' },
]
const statusOptions = [
  { label: 'OK', value: 'OK' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CANCELLED', value: 'CANCELLED' },
]
const turnStatusOptions = [
  { label: 'RUNNING', value: 'RUNNING' },
  { label: 'HITL', value: 'HITL' },
  { label: 'OK', value: 'OK' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CANCELLED', value: 'CANCELLED' },
]

const view = ref<'turns' | 'spans'>('turns')
const activeTurn = ref<askApi.AskTurnItem | null>(null)

const summaryBuckets = ref<
  Array<{ kind: string; status: string; count: number; avgLatencyMs: number }>
>([])
const loading = ref(false)

const turnItems = ref<askApi.AskTurnItem[]>([])
const turnFilters = reactive<{ status?: string }>({})
const turnPage = ref(1)
const turnPageSize = ref(20)
const turnTotal = ref(0)

const spanItems = ref<askApi.LlmSpanItem[]>([])
const spanFilters = reactive<{ kind?: string; status?: string }>({})
const spanPage = ref(1)
const spanPageSize = ref(20)
const spanTotal = ref(0)

const detailOpen = ref(false)
const detailDrawerWidth = ref(loadDrawerWidth())
const drawerResizing = ref(false)
let drawerResizeCleanup: (() => void) | null = null
const detailData = ref<Record<string, unknown> | null>(null)
const detailRounds = ref<LlmRound[]>([])
const roundActiveKeys = ref<string[]>(['0'])
const detailPayloadJson = computed(() =>
  JSON.stringify((detailData.value as { payloadMeta?: unknown } | null)?.payloadMeta ?? null, null, 2),
)

function onDrawerResizeStart(e: PointerEvent) {
  drawerResizeCleanup?.()
  drawerResizing.value = true
  const startX = e.clientX
  const startW = detailDrawerWidth.value
  const prevUserSelect = document.body.style.userSelect
  document.body.style.userSelect = 'none'

  const onMove = (ev: PointerEvent) => {
    // 右侧抽屉：向左拖加宽
    detailDrawerWidth.value = clampDrawerWidth(startW + (startX - ev.clientX))
  }
  const onUp = () => {
    drawerResizing.value = false
    document.body.style.userSelect = prevUserSelect
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    drawerResizeCleanup = null
    try {
      sessionStorage.setItem(DRAWER_WIDTH_KEY, String(detailDrawerWidth.value))
    } catch {
      /* ignore */
    }
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
  drawerResizeCleanup = onUp
}

const turnPagination = computed(() => ({
  current: turnPage.value,
  pageSize: turnPageSize.value,
  total: turnTotal.value,
  showSizeChanger: true,
}))

const spanPagination = computed(() => ({
  current: spanPage.value,
  pageSize: spanPageSize.value,
  total: spanTotal.value,
  showSizeChanger: true,
}))

const turnColumns = [
  { title: '问题', key: 'question', ellipsis: true },
  { title: '开始时间', dataIndex: 'startedAt', key: 'startedAt', width: 180 },
  { title: '结束时间', key: 'finishedAt', width: 180 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '耗时(毫秒)', key: 'latencyMs', width: 110 },
  { title: 'Token消耗', key: 'tokenTotal', width: 110 },
  { title: '操作', key: 'action', width: 80 },
]

const spanColumns = [
  { title: '编号', dataIndex: 'id', key: 'id', width: 80 },
  { title: '开始时间', dataIndex: 'startedAt', key: 'startedAt', width: 180 },
  { title: '阶段', dataIndex: 'phase', key: 'phase', width: 90 },
  { title: '类型', dataIndex: 'kind', key: 'kind', width: 90 },
  { title: '环节名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  { title: '耗时(毫秒)', dataIndex: 'latencyMs', key: 'latencyMs', width: 110 },
  { title: '输入Token', key: 'tokenIn', width: 100 },
  { title: '输出Token', key: 'tokenOut', width: 100 },
  { title: '模型', key: 'model', width: 140 },
  { title: '操作', key: 'action', width: 80 },
]

async function loadSummary() {
  try {
    const resp = await askApi.fetchLlmSummary(hours.value)
    summaryBuckets.value = resp.data?.buckets || []
  } catch {
    /* http 拦截器已提示 */
  }
}

async function loadTurns() {
  loading.value = true
  try {
    const resp = await askApi.fetchAskTurns({
      page: turnPage.value,
      size: turnPageSize.value,
      status: turnFilters.status,
    })
    turnItems.value = resp.data?.items || []
    turnTotal.value = resp.data?.total || 0
  } catch {
    /* http 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

async function loadSpans() {
  if (!activeTurn.value) return
  loading.value = true
  try {
    const resp = await askApi.fetchLlmSpans({
      page: spanPage.value,
      size: spanPageSize.value,
      kind: spanFilters.kind,
      status: spanFilters.status,
      turnId: activeTurn.value.id,
    })
    spanItems.value = resp.data?.items || []
    spanTotal.value = resp.data?.total || 0
  } catch {
    /* http 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function onTurnTableChange(pag: { current?: number; pageSize?: number }) {
  turnPage.value = pag.current || 1
  turnPageSize.value = pag.pageSize || 20
  loadTurns()
}

function onSpanTableChange(pag: { current?: number; pageSize?: number }) {
  spanPage.value = pag.current || 1
  spanPageSize.value = pag.pageSize || 20
  loadSpans()
}

function openTurnDetail(record: askApi.AskTurnItem) {
  activeTurn.value = record
  view.value = 'spans'
  spanPage.value = 1
  spanFilters.kind = undefined
  spanFilters.status = undefined
  loadSpans()
}

function backToTurns() {
  view.value = 'turns'
  activeTurn.value = null
  detailOpen.value = false
  loadTurns()
}

function formatMessages(prompt: unknown): string {
  if (prompt == null) return '—'
  if (typeof prompt === 'string') return prompt
  try {
    return JSON.stringify(prompt, null, 2)
  } catch {
    return String(prompt)
  }
}

function formatResponse(response: unknown): string {
  if (response == null) return '—'
  if (typeof response === 'string') return response
  try {
    return JSON.stringify(response, null, 2)
  } catch {
    return String(response)
  }
}

function roundPanelTitle(round: LlmRound, idx: number): string {
  const step = round.step != null ? round.step : idx
  const role = round.role ? ` · ${round.role}` : ''
  const child = round.childSpanId != null ? ` · 子#${round.childSpanId}` : ''
  return `第 ${Number(step) + 1} 轮${role}${child}`
}

async function openSpanDetail(id: number) {
  try {
    const resp = await askApi.fetchSpanDetail(id)
    const data = (resp.data || {}) as Record<string, unknown>
    detailData.value = data
    const rounds = Array.isArray(data.llmRounds) ? (data.llmRounds as LlmRound[]) : []
    detailRounds.value = rounds
    roundActiveKeys.value = rounds.length ? rounds.map((_, i) => String(i)) : []
    detailOpen.value = true
  } catch {
    /* http 拦截器已提示 */
  }
}

function reload() {
  loadSummary()
  if (view.value === 'turns') loadTurns()
  else loadSpans()
}

onMounted(reload)

onUnmounted(() => {
  drawerResizeCleanup?.()
})
</script>

<style scoped>
.page {
  padding: 16px 20px;
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.hd h2 {
  margin: 0;
  font-size: 18px;
}
.summary {
  margin-bottom: 12px;
}
.card-k {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.card-v {
  font-size: 22px;
  font-weight: 600;
  margin: 4px 0;
}
.card-s {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.back-btn {
  padding: 0;
  height: auto;
}
.turn-q {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.45);
  font-weight: 400;
  font-size: 13px;
}
.q-cell {
  display: inline-block;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.filters {
  margin-bottom: 12px;
}
.detail {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 320px;
  overflow: auto;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 8px;
}
.detail.muted {
  max-height: 200px;
  opacity: 0.85;
}
.meta-desc {
  margin-bottom: 16px;
}
.rounds-hd,
.raw-hd {
  margin: 16px 0 8px;
  font-weight: 600;
}
.round-block {
  margin-bottom: 12px;
}
.round-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 4px;
}
.round-note {
  font-size: 12px;
  color: #fa8c16;
}
</style>

<style>
.ask-span-drawer-resize-handle {
  position: fixed;
  top: 0;
  bottom: 0;
  width: 6px;
  margin-right: -3px;
  cursor: col-resize;
  z-index: 1100;
  background: transparent;
  touch-action: none;
}
.ask-span-drawer-resize-handle:hover,
.ask-span-drawer-resize-handle.dragging {
  background: rgba(22, 119, 255, 0.35);
}
.ask-span-detail-drawer.ant-drawer .ant-drawer-content-wrapper {
  transition: none;
}
</style>
