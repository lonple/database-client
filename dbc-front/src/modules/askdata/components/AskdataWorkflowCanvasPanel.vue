<template>
  <div class="wf-panel">
    <div class="panel-hd">
      <div class="hd-text">
        <h3>{{ title || '工作流画布' }}</h3>
        <div class="sub">{{ subtitle }}</div>
      </div>
      <div class="actions">
        <a-tooltip :title="!workflowId ? '该用例未生成工作流，无法执行' : null">
          <a-button type="primary" :loading="running" :disabled="!workflowId" @click="onExecute">
            执行
          </a-button>
        </a-tooltip>
        <a-button v-if="running && currentRunId" danger @click="onStop">停止</a-button>
      </div>
    </div>
    <div class="panel-body">
      <div class="canvas">
        <div class="canvas-top">
          <a-spin :spinning="loading">
            <a-empty v-if="!canvasNodes.length && !loading" :description="emptyHint" />
            <div v-else class="wf-canvas">
              <div class="wf-flow wf-flow-vertical">
                <template v-for="(n, idx) in canvasNodes" :key="n.id">
                  <div
                    class="wf-node"
                    :class="[n.type?.toLowerCase(), n.status, { selected: selectedNodeId === n.id }]"
                    @click="selectCanvasNode(n.id)"
                  >
                    <div class="nk">{{ nodeKindLabel(n) }}</div>
                    <div class="nt">{{ n.title || n.id }}</div>
                    <div class="nd">{{ nodePurpose(n) }}</div>
                    <div v-if="n.status" class="st" :class="n.status">{{ nodeStatusText(n.status) }}</div>
                  </div>
                  <div v-if="idx < canvasNodes.length - 1" class="wf-arrow wf-arrow-down" aria-hidden="true">
                    <span class="wf-arrow-line" />
                    <span class="wf-arrow-head" />
                    <span class="wf-arrow-label">数据流</span>
                  </div>
                </template>
              </div>
            </div>
          </a-spin>
        </div>
        <div class="console" :style="{ height: consoleHeight + 'px' }">
          <div class="console-resizer" @mousedown="onConsoleResizeStart" title="拖动调整高度" />
          <div class="console-hd">
            <button
              type="button"
              class="console-tab"
              :class="{ active: consoleTab === 'logs' }"
              @click="consoleTab = 'logs'"
            >
              执行日志
            </button>
            <button
              type="button"
              class="console-tab"
              :class="{ active: consoleTab === 'detail' }"
              @click="consoleTab = 'detail'"
            >
              节点详情
            </button>
            <button
              type="button"
              class="console-tab"
              :class="{ active: consoleTab === 'result' }"
              @click="consoleTab = 'result'"
            >
              结果
              <span v-if="resultRowCount != null" class="tab-badge">{{ resultRowCount }}</span>
            </button>
            <span class="console-status" :class="consoleStatusClass">{{ consoleStatusText }}</span>
          </div>
          <div v-show="consoleTab === 'logs'" class="console-body">
            <div v-if="!execLogs.length" class="console-empty">执行后这里显示步骤日志</div>
            <div v-for="(log, i) in execLogs" :key="i" class="log-line" :class="log.ok ? 'ok' : 'fail'">
              {{ log.message }}
            </div>
          </div>
          <div v-show="consoleTab === 'detail'" class="console-body detail-body">
            <a-empty v-if="!selectedNode" description="点击画布节点查看详情" />
            <template v-else>
              <div class="detail-meta">
                <div><span class="label">节点</span>{{ selectedNode.id }}</div>
                <div><span class="label">类型</span>{{ selectedNode.type }}</div>
                <div><span class="label">做什么</span>{{ selectedNode.title || selectedNode.id }}</div>
                <div><span class="label">说明</span>{{ nodePurpose(selectedNode) }}</div>
              </div>
              <div class="detail-sql-hd">SQL</div>
              <pre class="detail-sql">{{ selectedNode.sql || '（无 SQL）' }}</pre>
            </template>
          </div>
          <div v-show="consoleTab === 'result'" class="console-body result-body">
            <a-empty v-if="!resultColumns.length" description="暂无结果，执行成功后自动打开此页" />
            <a-table
              v-else
              size="small"
              :columns="resultColumns"
              :data-source="resultRows"
              :pagination="{ pageSize: 20, size: 'small' }"
              :scroll="{ x: true, y: Math.max(80, consoleHeight - 120) }"
            />
          </div>
        </div>
      </div>
      <aside class="ad-worklog" :class="{ busy: running }" :style="{ width: worklogWidth + 'px' }">
        <div class="worklog-resizer" @mousedown="onWorklogResizeStart" title="拖动调整宽度" />
        <div class="worklog-hd">
          <span>执行日志</span>
          <span v-if="running" class="live">执行中</span>
        </div>
        <div ref="worklogBody" class="worklog-body">
          <div v-if="!workLogs.length" class="worklog-empty">
            {{ worklogEmptyHint }}
          </div>
          <div v-for="(item, i) in workLogs" :key="i" class="worklog-line" :class="item.level.toLowerCase()">
            <span class="t">{{ formatLogTime(item.at) }}</span>
            <span class="m">{{ item.message }}</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import * as askApi from '@/modules/askdata/api/askdata'

type CanvasNode = { id: string; type: string; title?: string; sql?: string; status?: string }

const props = defineProps<{
  workflowId?: number | null
  runId?: number | null
  sessionId?: number | null
  title?: string
  /** 用例 askError，无工作流时展示在下侧执行日志 */
  caseError?: string | null
}>()

const loading = ref(false)
const running = ref(false)
const workflowName = ref('')
const canvasNodes = ref<CanvasNode[]>([])
const execLogs = ref<Array<{ message: string; ok: boolean }>>([])
const workLogs = ref<Array<{ at: string; level: string; message: string }>>([])
const workLogCursor = ref(0)
const currentRunId = ref<number | null>(null)
const resolvedSessionId = ref<number | null>(null)
const consoleTab = ref<'logs' | 'result' | 'detail'>('logs')
const consoleHeight = ref(220)
const worklogWidth = ref(260)
const selectedNodeId = ref<string | null>(null)
const lastRunStatus = ref<string | null>(null)
const resultColumns = ref<Array<{ title: string; dataIndex: string; key: string }>>([])
const resultRows = ref<Record<string, unknown>[]>([])
const resultRowCount = ref<number | null>(null)
const worklogBody = ref<HTMLElement | null>(null)

let workLogTimer: ReturnType<typeof setInterval> | null = null
let consoleResizing = false
let worklogResizing = false

const selectedNode = computed(() => canvasNodes.value.find((n) => n.id === selectedNodeId.value) || null)
const subtitle = computed(() => {
  const parts: string[] = []
  if (workflowName.value) parts.push(workflowName.value)
  if (props.workflowId) parts.push(`工作流 #${props.workflowId}`)
  else parts.push('无工作流')
  if (currentRunId.value) parts.push(`run #${currentRunId.value}`)
  if (resolvedSessionId.value) parts.push(`会话 #${resolvedSessionId.value}`)
  return parts.join(' · ')
})
const emptyHint = computed(() =>
  props.workflowId
    ? '工作流无节点'
    : '该用例未生成工作流，画布为空；请查看右侧执行日志',
)
const worklogEmptyHint = computed(() => {
  if (resolvedSessionId.value) {
    return '本轮暂无过程日志（与会话一致：仅展示 work-log；若刚跑完可稍后重开从库加载）'
  }
  return '无关联会话，无法加载执行日志'
})

const consoleStatusText = computed(() => {
  if (running.value) return '执行中…'
  if (lastRunStatus.value === 'SUCCESS') return '执行成功'
  if (lastRunStatus.value === 'FAILED') return '执行失败'
  if (lastRunStatus.value === 'STOPPED') return '已停止'
  return ''
})

const consoleStatusClass = computed(() => {
  if (running.value) return 'running'
  if (lastRunStatus.value === 'SUCCESS') return 'ok'
  if (lastRunStatus.value === 'FAILED') return 'fail'
  if (lastRunStatus.value === 'STOPPED') return 'stopped'
  return ''
})

function formatLogTime(at: string) {
  if (!at) return ''
  const d = new Date(at)
  if (Number.isNaN(d.getTime())) return at.slice(11, 19) || at
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

function nodeKindLabel(n: { type?: string; id: string }) {
  const t = (n.type || '').toUpperCase()
  if (t === 'GOVERN') return 'GOVERN · 历史中间表'
  if (t === 'QUERY') return 'QUERY · 查询'
  if (t === 'SQL') return 'SQL'
  return t || '节点'
}

function nodePurpose(n: { type?: string; title?: string; id: string }) {
  const t = (n.type || '').toUpperCase()
  if (t === 'GOVERN') return '历史草稿中间数据集（新生成仅单节点 QUERY）'
  if (t === 'QUERY') return '产出最终结果集'
  if (t === 'SQL') return 'SQL 数据变换'
  return n.title || '数据节点'
}

function nodeStatusText(status?: string) {
  if (status === 'ok') return '成功'
  if (status === 'fail') return '失败'
  if (status === 'run') return '执行中'
  return ''
}

function selectCanvasNode(id: string) {
  selectedNodeId.value = id
  consoleTab.value = 'detail'
}

function stopWorkLogPoll() {
  if (workLogTimer) {
    clearInterval(workLogTimer)
    workLogTimer = null
  }
}

function resetWorkLogs() {
  workLogs.value = []
  workLogCursor.value = 0
}

async function pullWorkLogs() {
  if (!resolvedSessionId.value) return
  try {
    const resp = await askApi.fetchWorkLogs(resolvedSessionId.value, workLogCursor.value)
    const data = resp.data
    if (!data) return
    const items = data.items || []
    if (items.length) {
      workLogs.value.push(...items)
      await nextTick()
      if (worklogBody.value) worklogBody.value.scrollTop = worklogBody.value.scrollHeight
    }
    if (typeof data.next === 'number') workLogCursor.value = data.next
  } catch {
    /* 轮询失败不打断主流程 */
  }
}

function startWorkLogPoll() {
  stopWorkLogPoll()
  void pullWorkLogs()
  workLogTimer = setInterval(() => {
    void pullWorkLogs()
  }, 800)
}

function applyResult(detail: askApi.RunDetail | null | undefined) {
  const cols = detail?.result?.columns || []
  const rows = detail?.result?.rows || []
  resultColumns.value = cols.map((c, idx) => ({
    title: c.name,
    dataIndex: `c${idx}`,
    key: `c${idx}`,
  }))
  resultRows.value = rows.map((r, i) => {
    const obj: Record<string, unknown> = { key: i }
    ;(r as unknown[]).forEach((cell, idx) => {
      obj[`c${idx}`] = cell
    })
    return obj
  })
  resultRowCount.value =
    detail?.result?.rowCount != null ? detail.result.rowCount : cols.length ? rows.length : null
}

function applyNodeStatusFromLogs(
  logs: Array<{ level?: string; message?: string }>,
  runStatus: string | null,
) {
  const okIds = new Set<string>()
  let failedId: string | null = null
  for (const log of logs) {
    const msg = log.message || ''
    const ok = msg.match(/节点\s+(\S+)\s+成功/)
    if (ok) okIds.add(ok[1])
  }
  if (runStatus === 'FAILED') {
    let lastStarted: string | null = null
    for (const log of logs) {
      const start = (log.message || '').match(/开始节点\s+(\S+)/)
      if (start) lastStarted = start[1]
      const ok = (log.message || '').match(/节点\s+(\S+)\s+成功/)
      if (ok && ok[1] === lastStarted) lastStarted = null
    }
    if (lastStarted) failedId = lastStarted
  }
  canvasNodes.value = canvasNodes.value.map((n) => {
    if (okIds.has(n.id)) return { ...n, status: 'ok' }
    if (failedId && n.id === failedId) return { ...n, status: 'fail' }
    if (runStatus === 'SUCCESS') return { ...n, status: 'ok' }
    return { ...n, status: '' }
  })
}

function applyCaseErrorToConsole() {
  const err = (props.caseError || '').trim()
  if (!err) return
  if (execLogs.value.some((l) => l.message === err)) return
  execLogs.value = [{ message: err, ok: false }, ...execLogs.value]
  consoleTab.value = 'logs'
}

async function loadRun(runId: number, switchResultTab: boolean) {
  const detail = (await askApi.fetchRun(runId)).data
  currentRunId.value = runId
  lastRunStatus.value = detail?.status || null
  if (detail?.sessionId) resolvedSessionId.value = detail.sessionId
  execLogs.value = (detail?.logs || []).map((log) => ({
    message: log.message,
    ok: log.level !== 'ERROR',
  }))
  applyNodeStatusFromLogs(detail?.logs || [], detail?.status || null)
  applyResult(detail)
  if (switchResultTab && detail?.status === 'SUCCESS') consoleTab.value = 'result'
  else consoleTab.value = 'logs'
}

async function loadAll() {
  loading.value = true
  canvasNodes.value = []
  execLogs.value = []
  applyResult(null)
  selectedNodeId.value = null
  lastRunStatus.value = null
  currentRunId.value = props.runId ?? null
  resolvedSessionId.value = props.sessionId ?? null
  workflowName.value = ''
  resetWorkLogs()
  stopWorkLogPoll()
  try {
    if (props.workflowId) {
      const resp = await askApi.fetchWorkflow(props.workflowId)
      workflowName.value = resp.data?.name || ''
      const nodes = (resp.data?.nodesJson as { nodes?: CanvasNode[] } | undefined)?.nodes || []
      canvasNodes.value = nodes.map((n) => ({
        id: n.id,
        type: n.type,
        title: n.title,
        sql: n.sql,
        status: '',
      }))
      if (props.runId) {
        await loadRun(props.runId, false)
      }
    }
    applyCaseErrorToConsole()
    if (resolvedSessionId.value) {
      // 与会话抽屉一致：只拉 work-log（热缓存 miss 时后端读库），不再用 LLM span 拼技术行
      await pullWorkLogs()
      if (props.workflowId) startWorkLogPoll()
    }
  } catch (e: any) {
    message.error(e?.message || '加载详情失败')
  } finally {
    loading.value = false
  }
}

async function onExecute() {
  if (!props.workflowId) return
  running.value = true
  execLogs.value = []
  lastRunStatus.value = null
  consoleTab.value = 'logs'
  canvasNodes.value = canvasNodes.value.map((n) => ({ ...n, status: 'run' }))
  if (resolvedSessionId.value) startWorkLogPoll()
  try {
    const resp = await askApi.startRun(props.workflowId, resolvedSessionId.value || undefined)
    const runId = resp.data?.id
    currentRunId.value = runId || null
    if (runId) await loadRun(runId, true)
    if (resp.data?.status === 'FAILED') {
      message.error(resp.data.errorMessage || '执行失败')
      consoleTab.value = 'logs'
    }
  } catch (e: any) {
    lastRunStatus.value = 'FAILED'
    canvasNodes.value = canvasNodes.value.map((n) => ({
      ...n,
      status: n.status === 'ok' ? 'ok' : 'fail',
    }))
    message.error(e?.message || '执行失败')
  } finally {
    running.value = false
  }
}

async function onStop() {
  if (!currentRunId.value) return
  try {
    await askApi.stopRun(currentRunId.value)
    lastRunStatus.value = 'STOPPED'
    message.info('已请求停止')
    running.value = false
  } catch (e: any) {
    message.error(e?.message || '停止失败')
  }
}

function onConsoleResizeStart(e: MouseEvent) {
  e.preventDefault()
  consoleResizing = true
  const startY = e.clientY
  const startH = consoleHeight.value
  const onMove = (ev: MouseEvent) => {
    if (!consoleResizing) return
    consoleHeight.value = Math.min(520, Math.max(140, startH + (startY - ev.clientY)))
  }
  const onUp = () => {
    consoleResizing = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onWorklogResizeStart(e: MouseEvent) {
  e.preventDefault()
  worklogResizing = true
  const startX = e.clientX
  const startW = worklogWidth.value
  const onMove = (ev: MouseEvent) => {
    if (!worklogResizing) return
    worklogWidth.value = Math.min(480, Math.max(180, startW + (startX - ev.clientX)))
  }
  const onUp = () => {
    worklogResizing = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

watch(
  () => [props.workflowId, props.runId, props.sessionId, props.caseError],
  () => {
    void loadAll()
  },
)

onMounted(() => {
  void loadAll()
})

onUnmounted(() => {
  stopWorkLogPoll()
})
</script>

<style scoped>
.wf-panel {
  display: flex;
  flex-direction: column;
  height: 72vh;
  min-height: 480px;
  background: #f5f5f5;
}
.panel-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  gap: 12px;
  flex-shrink: 0;
}
.panel-hd h3 {
  margin: 0;
  font-size: 15px;
}
.sub {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 2px;
}
.actions {
  display: flex;
  gap: 8px;
}
.panel-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.canvas-top {
  flex: 1;
  overflow: auto;
  padding: 16px;
  min-height: 120px;
}
.wf-canvas {
  min-height: 200px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 24px;
  overflow: auto;
  background-color: #fff;
  background-image: radial-gradient(#e8e8e8 1px, transparent 1px);
  background-size: 16px 16px;
}
.wf-flow-vertical {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.wf-node {
  position: relative;
  width: min(360px, 92%);
  flex-shrink: 0;
  background: #fff;
  border: 1.5px solid #d9d9d9;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.wf-node::before,
.wf-node::after {
  content: '';
  position: absolute;
  left: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #bfbfbf;
  border: 2px solid #fff;
  transform: translateX(-50%);
}
.wf-node::before {
  top: -5px;
}
.wf-node::after {
  bottom: -5px;
}
.wf-flow-vertical > .wf-node:first-child::before,
.wf-flow-vertical > .wf-node:last-child::after {
  display: none;
}
.wf-node.selected {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.18);
}
.wf-node.govern {
  border-color: #d48806;
}
.wf-node.query {
  border-color: #389e0d;
}
.wf-node.ok {
  background: #f6ffed;
  border-color: #389e0d;
}
.wf-node.fail {
  background: #fff2f0;
  border-color: #ff4d4f;
}
.wf-node.run {
  background: #e6f4ff;
  border-color: #1677ff;
}
.wf-node .nk {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 6px;
}
.wf-node .nt {
  font-weight: 600;
  font-size: 14px;
}
.wf-node .nd {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 8px;
}
.wf-node .st {
  font-size: 12px;
  margin-top: 10px;
  font-weight: 600;
}
.wf-node .st.ok {
  color: #389e0d;
}
.wf-node .st.fail {
  color: #cf1322;
}
.wf-node .st.run {
  color: #1677ff;
}
.wf-arrow-down {
  position: relative;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.wf-arrow-down .wf-arrow-line {
  display: block;
  width: 2px;
  height: 100%;
  background: #8c8c8c;
}
.wf-arrow-down .wf-arrow-head {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 10px 6px 0 6px;
  border-color: #8c8c8c transparent transparent transparent;
}
.wf-arrow-down .wf-arrow-label {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: rgba(0, 0, 0, 0.45);
  white-space: nowrap;
  background: #fff;
  padding: 0 4px;
}
.console {
  position: relative;
  flex-shrink: 0;
  border-top: 1px solid #f0f0f0;
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 140px;
}
.console-resizer {
  position: absolute;
  top: -3px;
  left: 0;
  right: 0;
  height: 6px;
  cursor: ns-resize;
  z-index: 2;
}
.console-hd {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}
.console-tab {
  border: none;
  background: transparent;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.65);
}
.console-tab.active {
  background: #fff;
  color: #1677ff;
  font-weight: 600;
  box-shadow: 0 0 0 1px #f0f0f0;
}
.tab-badge {
  margin-left: 4px;
  font-size: 11px;
  color: rgba(0, 0, 0, 0.45);
}
.console-status {
  margin-left: auto;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.console-status.running {
  color: #1677ff;
}
.console-status.ok {
  color: #389e0d;
}
.console-status.fail {
  color: #cf1322;
}
.console-status.stopped {
  color: #d46b08;
}
.console-body {
  flex: 1;
  overflow: auto;
  padding: 8px 12px;
  font-size: 12px;
  min-height: 0;
}
.console-empty {
  color: rgba(0, 0, 0, 0.45);
}
.result-body {
  padding: 8px;
}
.log-line {
  padding: 2px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.log-line.ok {
  color: #389e0d;
}
.log-line.fail {
  color: #cf1322;
}
.detail-meta {
  display: grid;
  gap: 6px;
  font-size: 12px;
  margin-bottom: 10px;
}
.detail-meta .label {
  display: inline-block;
  min-width: 48px;
  color: rgba(0, 0, 0, 0.45);
  margin-right: 8px;
}
.detail-sql-hd {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}
.detail-sql {
  margin: 0;
  padding: 10px 12px;
  background: #1f1f1f;
  color: #f0f0f0;
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.ad-worklog {
  position: relative;
  flex-shrink: 0;
  background: #111827;
  color: #e5e7eb;
  border-left: 1px solid #1f2937;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.worklog-resizer {
  position: absolute;
  top: 0;
  left: -3px;
  width: 6px;
  height: 100%;
  cursor: ew-resize;
  z-index: 2;
}
.worklog-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #1f2937;
  font-weight: 600;
  font-size: 13px;
}
.worklog-hd .live {
  font-size: 11px;
  color: #34d399;
}
.worklog-body {
  flex: 1;
  overflow: auto;
  padding: 10px 12px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.worklog-empty {
  color: #9ca3af;
}
.worklog-line {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.worklog-line .t {
  color: #6b7280;
  flex-shrink: 0;
}
.worklog-line .m {
  color: #d1d5db;
  word-break: break-word;
}
.worklog-line.error .m {
  color: #fca5a5;
}
</style>
