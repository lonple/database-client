<template>
  <div class="ad-layout">
    <aside class="ad-side">
      <div class="side-hd">
        <span>工程</span>
        <a-button type="link" size="small" @click="openCreate">新建</a-button>
      </div>
      <a-spin :spinning="treeLoading">
        <div class="tree" @click="closeCtxMenu">
          <a-empty v-if="!tree.length && !treeLoading" description="暂无工程" :image="simpleImage" />
          <details v-for="p in tree" :key="p.id" open>
            <summary
              :class="{ active: activeProjectId === p.id && !activeWorkflowId }"
              @click.prevent="selectProject(p)"
              @contextmenu.prevent.stop="openCtxMenu($event, 'project', p)"
            >
              <span class="proj">{{ p.name }}</span>
              <span class="desc">
                来源 {{ formatScope(p.sourceConnectionId, p.sourceDatabase, p.sourceSchema) }}
                · 工作 {{ formatScope(p.workConnectionId, p.workDatabase, p.workSchema) }}
              </span>
              <span v-if="p.description" class="desc">{{ p.description }}</span>
            </summary>
            <div
              v-for="w in p.workflows"
              :key="w.id"
              class="wf"
              :class="{ active: activeWorkflowId === w.id }"
              @click="openWorkflow(p, w.id)"
              @contextmenu.prevent.stop="openCtxMenu($event, 'workflow', p, w)"
            >
              <span class="kind">流</span>{{ w.name }}
            </div>
          </details>
        </div>
      </a-spin>

      <Teleport to="body">
        <div
          v-if="ctxMenu.visible"
          class="ad-ctx-mask"
          @click="closeCtxMenu"
          @contextmenu.prevent="closeCtxMenu"
        >
          <ul
            class="ad-ctx-menu"
            :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }"
            @click.stop
          >
            <li class="danger" @click="onCtxDelete">
              {{ ctxMenu.kind === 'project' ? '删除工程' : '删除工作流' }}
            </li>
          </ul>
        </div>
      </Teleport>
    </aside>

    <main class="ad-main">
      <div class="panel-hd">
        <div>
          <h3>{{ panelTitle }}</h3>
          <div class="sub">{{ panelSub }}</div>
        </div>
        <div class="actions">
          <a-button size="small" @click="backToSpaces">返回空间切换</a-button>
          <a-radio-group v-model:value="mode" button-style="solid" size="small">
            <a-radio-button value="chat">对话</a-radio-button>
            <a-radio-button value="canvas">画布</a-radio-button>
          </a-radio-group>
          <a-button
            v-if="mode === 'chat' && sessionId"
            :disabled="!messages.length && !workLogs.length"
            @click="onClearSession"
          >
            清空会话
          </a-button>
          <a-button
            v-if="mode === 'canvas' && activeWorkflowId"
            type="primary"
            :loading="running"
            @click="onExecute"
          >
            执行
          </a-button>
          <a-button v-if="running && currentRunId" danger @click="onStop">停止</a-button>
        </div>
      </div>

      <div v-show="mode === 'chat'" class="chat">
        <div ref="chatBody" class="chat-body">
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
            <div class="bubble">{{ m.content }}</div>
            <div v-if="m.hitlId && m.showHitl" class="hitl">
              <h4>需要确认</h4>
              <p>{{ m.content }}</p>
              <a-space direction="vertical" style="width: 100%">
                <a-input
                  v-model:value="hitlNote"
                  placeholder="补充真实码值 / 口径（可选；不要填口语缩写）"
                />
                <a-button type="primary" size="small" :loading="hitlLoading" @click="onResolveHitl(m.hitlId!)">
                  确认并继续生成
                </a-button>
              </a-space>
            </div>
            <div v-if="m.draftId && m.draft" class="save-card">
              <h4>可保存工作流</h4>
              <p>{{ m.draft.name || '草稿' }}</p>
              <a-space>
                <a-button type="primary" size="small" @click="onSaveDraft(m)">保存到工程</a-button>
                <a-button size="small" :loading="running" @click="onSaveAndRun(m)">保存并执行</a-button>
              </a-space>
            </div>
          </div>
        </div>
        <div class="composer">
          <a-textarea
            v-model:value="input"
            :rows="2"
            placeholder="用自然语言描述要查的数据…（Enter 发送，Shift+Enter 换行）"
            :disabled="!activeProjectId || chatting"
            @keydown="onComposerKeydown"
          />
          <a-button type="primary" :loading="chatting" :disabled="!activeProjectId || !input.trim()" @click="onSend">
            发送
          </a-button>
        </div>
      </div>

      <div v-show="mode === 'canvas'" class="canvas">
        <div class="canvas-top">
          <a-empty v-if="!canvasNodes.length" description="请选择已保存的工作流，或先在对话中生成并保存" />
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
    </main>

    <aside
      class="ad-worklog"
      :class="{ busy: chatting || hitlLoading || running }"
      :style="{ width: worklogWidth + 'px' }"
    >
      <div class="worklog-resizer" @mousedown="onWorklogResizeStart" title="拖动调整宽度" />
      <div class="worklog-hd">
        <span>业务工作日志</span>
        <span v-if="chatting || hitlLoading" class="live">处理中</span>
        <span v-else-if="running" class="live">执行中</span>
      </div>
      <div ref="worklogBody" class="worklog-body">
        <div v-if="!workLogs.length" class="worklog-empty">
          {{ sessionId ? '发送问题后，这里会实时显示系统在做什么' : '请先选择工程' }}
        </div>
        <div v-for="(item, i) in workLogs" :key="i" class="worklog-line" :class="item.level.toLowerCase()">
          <span class="t">{{ formatLogTime(item.at) }}</span>
          <span class="m">{{ item.message }}</span>
        </div>
      </div>
    </aside>

    <a-modal
      v-model:open="createOpen"
      title="新建工程"
      width="560px"
      @ok="submitCreate"
      :confirm-loading="creating"
    >
      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="createForm.name" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="createForm.description" />
        </a-form-item>
        <a-divider orientation="left" plain>数据来源</a-divider>
        <p class="form-hint">生成/探测默认在此作用域检索表结构（连接 → 库 → 模式随库类型变化）。</p>
        <ConnectionScopePicker
          v-model="createForm.source"
          :workspace-id="workspaceId"
          :connections="connections"
          connection-label="来源连接"
          connection-placeholder="选择数据来源连接"
        />
        <a-divider orientation="left" plain>工作连接</a-divider>
        <p class="form-hint">临时表与结果表落此作用域（须有建表/写权限）。</p>
        <ConnectionScopePicker
          v-model="createForm.work"
          :workspace-id="workspaceId"
          :connections="connections"
          connection-label="工作连接"
          connection-placeholder="选择工作连接"
        />
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Empty, Modal, message } from 'ant-design-vue'
import * as askApi from '@/modules/askdata/api/askdata'
import ConnectionScopePicker, {
  type ConnectionScopeValue,
} from '@/modules/askdata/components/ConnectionScopePicker.vue'
import { isPgStyle } from '@/modules/auth/utils/objectGrant'
import { listWorkspaceConnections, type ConnectionSummary } from '@/modules/sqlwork/api/sqlwork'

type UiMessage = {
  role: string
  content: string
  draftId?: number | null
  hitlId?: number | null
  showHitl?: boolean
  draft?: askApi.ChatResponse['draft']
}

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => Number(route.params.workspaceId))

function backToSpaces() {
  router.push({ name: 'askdata-spaces' })
}

const tree = ref<askApi.TreeProject[]>([])
const treeLoading = ref(false)
const activeProjectId = ref<number | null>(null)
const activeWorkflowId = ref<number | null>(null)
const sessionId = ref<number | null>(null)
const mode = ref<'chat' | 'canvas'>('chat')
const input = ref('')
const chatting = ref(false)
const running = ref(false)
const messages = ref<UiMessage[]>([])
const execLogs = ref<Array<{ message: string; ok: boolean; runId?: number }>>([])
const workLogs = ref<Array<{ at: string; level: string; message: string }>>([])
const workLogCursor = ref(0)
const canvasNodes = ref<Array<{ id: string; type: string; title?: string; sql?: string; status?: string }>>([])
const connections = ref<ConnectionSummary[]>([])
const createOpen = ref(false)
const creating = ref(false)
const createForm = reactive({
  name: '',
  description: '',
  source: {} as ConnectionScopeValue,
  work: {} as ConnectionScopeValue,
})
const hitlNote = ref('')
const hitlLoading = ref(false)
const currentRunId = ref<number | null>(null)
const consoleTab = ref<'logs' | 'result' | 'detail'>('logs')
const consoleHeight = ref(220)
const worklogWidth = ref(280)
const selectedNodeId = ref<string | null>(null)
const lastRunStatus = ref<string | null>(null)
const resultColumns = ref<Array<{ title: string; dataIndex: string; key: string }>>([])
const resultRows = ref<Record<string, unknown>[]>([])
const resultRowCount = ref<number | null>(null)
const chatBody = ref<HTMLElement | null>(null)
const worklogBody = ref<HTMLElement | null>(null)

let workLogTimer: ReturnType<typeof setInterval> | null = null
let consoleResizing = false

const selectedNode = computed(() => canvasNodes.value.find((n) => n.id === selectedNodeId.value) || null)

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

function formatScope(
  connectionId?: number | null,
  database?: string | null,
  schema?: string | null,
) {
  const conn = connections.value.find((c) => c.connectionId === connectionId)
  const name = conn?.name || (connectionId != null ? `#${connectionId}` : '-')
  const parts = [name]
  if (database) parts.push(database)
  if (schema) parts.push(schema)
  return parts.join(' / ')
}

function formatLogTime(at: string) {
  if (!at) return ''
  const d = new Date(at)
  if (Number.isNaN(d.getTime())) return at.slice(11, 19) || at
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

function nodeKindLabel(n: { type?: string; id: string }) {
  const t = (n.type || '').toUpperCase()
  if (t === 'GOVERN') return 'GOVERN · 清洗落表'
  if (t === 'QUERY') return 'QUERY · 查询'
  if (t === 'SQL') return 'SQL'
  return t || '节点'
}

function nodePurpose(n: { type?: string; title?: string; id: string }) {
  const t = (n.type || '').toUpperCase()
  if (t === 'GOVERN') return '产出中间数据集（写入工作连接临时表）'
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

async function onClearSession() {
  if (!sessionId.value) return
  Modal.confirm({
    title: '清空会话',
    content: '确认清空当前会话的全部对话内容？此操作不可恢复。',
    okText: '清空',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await askApi.clearSessionMessages(sessionId.value!)
        messages.value = []
        resetWorkLogs()
        hitlNote.value = ''
        message.success('会话已清空')
      } catch (e: any) {
        message.error(e?.message || '清空失败')
        throw e
      }
    },
  })
}

function validateScope(label: string, scope: ConnectionScopeValue): string | null {
  if (!scope.connectionId) return `请选择${label}连接`
  if (!scope.database?.trim()) return `请选择${label}库`
  const conn = connections.value.find((c) => c.connectionId === scope.connectionId)
  if (conn && isPgStyle(conn.dbType) && !scope.schema?.trim()) {
    return `请选择${label}模式`
  }
  return null
}

const panelTitle = computed(() => {
  const p = tree.value.find((x) => x.id === activeProjectId.value)
  if (activeWorkflowId.value) {
    const w = p?.workflows.find((x) => x.id === activeWorkflowId.value)
    return w?.name || '工作流'
  }
  return p?.name || '智能问数'
})

const panelSub = computed(() => {
  const p = tree.value.find((x) => x.id === activeProjectId.value)
  if (!p) return '请选择或新建工程'
  return `来源 ${formatScope(p.sourceConnectionId, p.sourceDatabase, p.sourceSchema)} · 工作 ${formatScope(p.workConnectionId, p.workDatabase, p.workSchema)}`
})

async function loadTree() {
  treeLoading.value = true
  try {
    const resp = await askApi.fetchTree(workspaceId.value)
    tree.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载目录失败')
  } finally {
    treeLoading.value = false
  }
}

async function loadConnections() {
  try {
    const resp = await listWorkspaceConnections(workspaceId.value)
    connections.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载连接失败')
  }
}

function openCreate() {
  createForm.name = ''
  createForm.description = ''
  createForm.source = {}
  createForm.work = {}
  createOpen.value = true
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    message.warning('请填写名称')
    return
  }
  const sourceErr = validateScope('数据来源', createForm.source)
  if (sourceErr) {
    message.warning(sourceErr)
    return
  }
  const workErr = validateScope('工作', createForm.work)
  if (workErr) {
    message.warning(workErr)
    return
  }
  creating.value = true
  try {
    const sourceConn = connections.value.find((c) => c.connectionId === createForm.source.connectionId)
    const workConn = connections.value.find((c) => c.connectionId === createForm.work.connectionId)
    await askApi.createProject({
      workspaceId: workspaceId.value,
      name: createForm.name.trim(),
      description: createForm.description || undefined,
      sourceConnectionId: createForm.source.connectionId!,
      sourceDatabase: createForm.source.database!,
      sourceSchema: sourceConn && isPgStyle(sourceConn.dbType) ? createForm.source.schema : undefined,
      workConnectionId: createForm.work.connectionId!,
      workDatabase: createForm.work.database!,
      workSchema: workConn && isPgStyle(workConn.dbType) ? createForm.work.schema : undefined,
    })
    message.success('工程已创建')
    createOpen.value = false
    await loadTree()
  } catch (e: any) {
    message.error(e?.message || '创建失败')
  } finally {
    creating.value = false
  }
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
  if (!sessionId.value) return
  try {
    const resp = await askApi.fetchWorkLogs(sessionId.value, workLogCursor.value)
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

function mapRestoredMessages(
  rows: askApi.SessionMessage[],
  pendingHitlId?: number | null,
): UiMessage[] {
  return (rows || []).map((m) => {
    const hitlId = m.payload?.hitlId ?? null
    return {
      role: m.role,
      content: m.content,
      draftId: m.payload?.draftId ?? null,
      hitlId,
      showHitl: !!(hitlId && pendingHitlId && hitlId === pendingHitlId),
      draft: m.payload?.draft,
    }
  })
}

async function selectProject(p: askApi.TreeProject) {
  activeProjectId.value = p.id
  activeWorkflowId.value = null
  mode.value = 'chat'
  canvasNodes.value = []
  execLogs.value = []
  resetWorkLogs()
  try {
    const resp = await askApi.openSession(p.id, `${p.name} 会话`)
    const data = resp.data
    sessionId.value = data?.id || null
    messages.value = mapRestoredMessages(data?.messages || [], data?.pendingHitlId)
    startWorkLogPoll()
    await nextTick()
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  } catch (e: any) {
    sessionId.value = null
    messages.value = []
    message.error(e?.message || '打开会话失败')
  }
}

async function openWorkflow(p: askApi.TreeProject, workflowId: number) {
  activeProjectId.value = p.id
  activeWorkflowId.value = workflowId
  mode.value = 'canvas'
  if (!sessionId.value || activeProjectId.value !== p.id) {
    try {
      const resp = await askApi.openSession(p.id, `${p.name} 会话`)
      sessionId.value = resp.data?.id || null
      messages.value = mapRestoredMessages(resp.data?.messages || [], resp.data?.pendingHitlId)
      resetWorkLogs()
      startWorkLogPoll()
    } catch (e: any) {
      message.error(e?.message || '打开会话失败')
    }
  }
  try {
    const resp = await askApi.fetchWorkflow(workflowId)
    const nodes = (resp.data?.nodesJson as any)?.nodes || []
    canvasNodes.value = nodes.map((n: any) => ({
      id: n.id,
      type: n.type,
      title: n.title,
      sql: n.sql,
      status: '',
    }))
    selectedNodeId.value = null
    consoleTab.value = 'logs'
  } catch (e: any) {
    message.error(e?.message || '加载工作流失败')
  }
}

function onComposerKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter' || e.shiftKey) return
  e.preventDefault()
  if (chatting.value || !input.value.trim()) return
  void onSend()
}

async function onSend() {
  if (!sessionId.value || !input.value.trim() || chatting.value) return
  const text = input.value.trim()
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  chatting.value = true
  resetWorkLogs()
  workLogs.value.push({
    at: new Date().toISOString(),
    level: 'INFO',
    message: `已发送，等待服务处理…`,
  })
  startWorkLogPoll()
  try {
    const resp = await askApi.chat(sessionId.value, text)
    const data = resp.data
    messages.value.forEach((m) => {
      if (m.showHitl) m.showHitl = false
    })
    messages.value.push({
      role: 'assistant',
      content: data?.reply || '',
      draftId: data?.draftId,
      hitlId: data?.hitlId,
      showHitl: !!(data?.needsHitl && data?.hitlId),
      draft: data?.draft,
    })
    await pullWorkLogs()
    await nextTick()
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  } catch (e: any) {
    workLogs.value.push({
      at: new Date().toISOString(),
      level: 'ERROR',
      message: e?.message || '对话失败',
    })
    message.error(e?.message || '对话失败')
  } finally {
    chatting.value = false
  }
}

async function onSaveDraft(m: UiMessage) {
  if (!activeProjectId.value || !m.draft || !m.draftId) return
  try {
    const resp = await askApi.saveWorkflow({
      projectId: activeProjectId.value,
      name: m.draft.name || '未命名工作流',
      nodesJson: m.draft as Record<string, unknown>,
      draftId: m.draftId,
    })
    message.success('已保存')
    m.draftId = null
    await loadTree()
    return resp.data?.id
  } catch (e: any) {
    message.error(e?.message || '保存失败')
    return null
  }
}

async function onSaveAndRun(m: UiMessage) {
  const wfId = await onSaveDraft(m)
  if (!wfId || !activeProjectId.value) return
  await loadTree()
  const p = tree.value.find((x) => x.id === activeProjectId.value)
  if (!p) {
    message.error('保存后未找到工程')
    return
  }
  activeWorkflowId.value = wfId
  mode.value = 'canvas'
  await openWorkflow(p, wfId)
  await onExecute()
}

async function onResolveHitl(hitlId: number) {
  hitlLoading.value = true
  startWorkLogPoll()
  try {
    const note = hitlNote.value.trim()
    const resp = await askApi.resolveHitl(hitlId, {
      ack: true,
      text: note || undefined,
      route: 'QUERY',
    })
    const data = resp.data as any
    messages.value.forEach((m) => {
      if (m.hitlId === hitlId) m.showHitl = false
    })
    messages.value.push({
      role: 'assistant',
      content: data?.reply || '已继续',
      draftId: data?.draftId,
      draft: data?.draft,
      hitlId: data?.needsHitl ? data?.id : null,
      showHitl: !!data?.needsHitl,
    })
    hitlNote.value = ''
    await pullWorkLogs()
    message.success('已确认并继续')
  } catch (e: any) {
    message.error(e?.message || '确认失败')
  } finally {
    hitlLoading.value = false
  }
}

async function onExecute() {
  if (!activeWorkflowId.value) return
  running.value = true
  execLogs.value = []
  lastRunStatus.value = null
  consoleTab.value = 'logs'
  canvasNodes.value = canvasNodes.value.map((n) => ({ ...n, status: 'run' }))
  startWorkLogPoll()
  try {
    const resp = await askApi.startRun(activeWorkflowId.value, sessionId.value || undefined)
    const runId = resp.data?.id
    currentRunId.value = runId || null
    const detail = runId ? (await askApi.fetchRun(runId)).data : null
    for (const log of detail?.logs || []) {
      execLogs.value.push({ message: log.message, ok: log.level !== 'ERROR', runId })
    }
    lastRunStatus.value = detail?.status || null
    applyNodeStatusFromLogs(detail?.logs || [], detail?.status || null)
    if (detail?.status === 'SUCCESS') {
      if (runId) await loadResult(runId, true)
    } else if (detail?.status === 'FAILED') {
      message.error(detail.errorMessage || '执行失败')
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
    const start = msg.match(/开始节点\s+(\S+)/)
    if (start && (log.level || '').toUpperCase() === 'ERROR') failedId = start[1]
  }
  if (runStatus === 'FAILED') {
    const errLog = [...logs].reverse().find((l) => (l.level || '').toUpperCase() === 'ERROR')
    if (errLog?.message) {
      // 失败发生在最后一个「开始节点」之后且未成功的节点
      let lastStarted: string | null = null
      for (const log of logs) {
        const start = (log.message || '').match(/开始节点\s+(\S+)/)
        if (start) lastStarted = start[1]
        const ok = (log.message || '').match(/节点\s+(\S+)\s+成功/)
        if (ok && ok[1] === lastStarted) lastStarted = null
      }
      if (lastStarted) failedId = lastStarted
    }
  }
  canvasNodes.value = canvasNodes.value.map((n) => {
    if (okIds.has(n.id)) return { ...n, status: 'ok' }
    if (failedId && n.id === failedId) return { ...n, status: 'fail' }
    if (runStatus === 'SUCCESS') return { ...n, status: 'ok' }
    return { ...n, status: '' }
  })
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

async function loadResult(runId: number, switchTab: boolean) {
  try {
    const detail = (await askApi.fetchRun(runId)).data
    applyResult(detail)
    if (switchTab) consoleTab.value = 'result'
  } catch (e: any) {
    message.error(e?.message || '加载结果失败')
  }
}

async function openResultTab(runId: number) {
  mode.value = 'canvas'
  await loadResult(runId, true)
}

function onConsoleResizeStart(e: MouseEvent) {
  e.preventDefault()
  consoleResizing = true
  const startY = e.clientY
  const startH = consoleHeight.value
  const onMove = (ev: MouseEvent) => {
    if (!consoleResizing) return
    const next = startH + (startY - ev.clientY)
    consoleHeight.value = Math.min(520, Math.max(140, next))
  }
  const onUp = () => {
    consoleResizing = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

let worklogResizing = false

function onWorklogResizeStart(e: MouseEvent) {
  e.preventDefault()
  worklogResizing = true
  const startX = e.clientX
  const startW = worklogWidth.value
  const onMove = (ev: MouseEvent) => {
    if (!worklogResizing) return
    const next = startW + (startX - ev.clientX)
    worklogWidth.value = Math.min(560, Math.max(200, next))
  }
  const onUp = () => {
    worklogResizing = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

const ctxMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  kind: 'project' as 'project' | 'workflow',
  project: null as askApi.TreeProject | null,
  workflow: null as askApi.TreeWorkflow | null,
})

function openCtxMenu(
  e: MouseEvent,
  kind: 'project' | 'workflow',
  project: askApi.TreeProject,
  workflow?: askApi.TreeWorkflow,
) {
  ctxMenu.visible = true
  ctxMenu.x = e.clientX
  ctxMenu.y = e.clientY
  ctxMenu.kind = kind
  ctxMenu.project = project
  ctxMenu.workflow = workflow || null
}

function closeCtxMenu() {
  ctxMenu.visible = false
}

function onCtxDelete() {
  const project = ctxMenu.project
  const workflow = ctxMenu.workflow
  const kind = ctxMenu.kind
  closeCtxMenu()
  if (!project) return
  if (kind === 'project') {
    Modal.confirm({
      title: '删除工程',
      content: `确认删除工程「${project.name}」？其下工作流将一并删除。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        await askApi.deleteProject(project.id)
        if (activeProjectId.value === project.id) {
          activeProjectId.value = null
          activeWorkflowId.value = null
          sessionId.value = null
          messages.value = []
          canvasNodes.value = []
          execLogs.value = []
          applyResult(null)
          stopWorkLogPoll()
        }
        message.success('工程已删除')
        await loadTree()
      },
    })
    return
  }
  if (!workflow) return
  Modal.confirm({
    title: '删除工作流',
    content: `确认删除工作流「${workflow.name}」？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      await askApi.deleteWorkflow(workflow.id)
      if (activeWorkflowId.value === workflow.id) {
        activeWorkflowId.value = null
        canvasNodes.value = []
        mode.value = 'chat'
      }
      message.success('工作流已删除')
      await loadTree()
    },
  })
}

onMounted(async () => {
  await Promise.all([loadTree(), loadConnections()])
})

onUnmounted(() => {
  stopWorkLogPoll()
})
</script>

<style scoped>
.ad-layout {
  display: flex;
  height: 100%;
  background: #f5f5f5;
}
.ad-side {
  width: 280px;
  background: #fafafa;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}
.side-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  font-weight: 500;
}
.tree {
  padding: 8px 0;
  overflow: auto;
  flex: 1;
  font-size: 13px;
}
.tree summary {
  list-style: none;
  cursor: pointer;
  padding: 8px 10px;
  margin: 1px 6px;
  border-radius: 6px;
}
.tree summary::-webkit-details-marker {
  display: none;
}
.tree summary.active,
.wf.active {
  background: #e6f4ff;
  color: #1677ff;
}
.proj {
  font-weight: 600;
}
.desc {
  display: block;
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  font-weight: 400;
}
.form-hint {
  margin: -4px 0 8px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.wf {
  padding: 6px 10px 6px 28px;
  margin: 1px 6px;
  border-radius: 6px;
  cursor: pointer;
}
.kind {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.45);
  margin-right: 4px;
}
.ad-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.ad-worklog {
  position: relative;
  width: 280px;
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
.worklog-resizer:hover,
.worklog-resizer:active {
  background: rgba(52, 211, 153, 0.35);
}
.ad-worklog.busy .worklog-hd .live {
  display: inline-flex;
}
.worklog-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #1f2937;
  font-weight: 600;
  font-size: 13px;
  color: #f9fafb;
}
.worklog-hd .live {
  display: none;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #34d399;
}
.worklog-hd .live::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #34d399;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.worklog-body {
  flex: 1;
  overflow: auto;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.worklog-empty {
  color: #9ca3af;
  padding: 8px 0;
}
.worklog-line {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.worklog-line .t {
  flex: 0 0 auto;
  color: #6b7280;
}
.worklog-line .m {
  color: #d1d5db;
  word-break: break-word;
}
.worklog-line.error .m {
  color: #fca5a5;
}
.worklog-line.warn .m {
  color: #fcd34d;
}
.panel-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  gap: 12px;
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
  align-items: center;
}
.chat,
.canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.chat-body {
  flex: 1;
  overflow: auto;
  padding: 16px;
}
.msg {
  margin-bottom: 12px;
  max-width: 92%;
}
.msg.user {
  margin-left: auto;
}
.bubble {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  white-space: pre-wrap;
  line-height: 1.5;
}
.msg.user .bubble {
  background: #1677ff;
  color: #fff;
}
.msg.assistant .bubble {
  background: #fff;
  border: 1px solid #f0f0f0;
}
.save-card,
.hitl {
  max-width: 92%;
  border-radius: 8px;
  padding: 12px;
  margin: 10px 0;
  font-size: 13px;
}
.save-card {
  border: 1px solid #91caff;
  background: #e6f4ff;
}
.hitl {
  border: 1px solid #ffe58f;
  background: #fffbe6;
}
.save-card h4,
.hitl h4 {
  margin: 0 0 6px;
  font-size: 13px;
}
.step {
  border: 1px solid #91caff;
  background: #f0f7ff;
  border-radius: 6px;
  padding: 8px 10px;
  margin: 8px 0;
  font-size: 12px;
  max-width: 92%;
}
.step .k {
  display: inline-block;
  padding: 0 6px;
  margin-right: 6px;
  border-radius: 4px;
  background: #eee;
  font-weight: 600;
}
.step.ok .k {
  background: #b7eb8f;
}
.step.fail .k {
  background: #ffccc7;
}
.composer {
  border-top: 1px solid #f0f0f0;
  padding: 10px 16px;
  background: #fff;
  display: flex;
  gap: 8px;
}
.canvas-top {
  flex: 1;
  overflow: auto;
  padding: 20px 16px;
  min-height: 120px;
}
.wf-canvas {
  min-height: 220px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 28px 24px;
  overflow: auto;
  background-color: #fff;
  background-image: radial-gradient(#e8e8e8 1px, transparent 1px);
  background-size: 16px 16px;
}
.wf-flow-vertical {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  min-height: 100%;
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
  transition: border-color 0.15s, box-shadow 0.15s;
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
  z-index: 1;
}
.wf-node::before {
  top: -5px;
}
.wf-node::after {
  bottom: -5px;
}
.wf-flow-vertical > .wf-node:first-child::before {
  display: none;
}
.wf-flow-vertical > .wf-node:last-child::after {
  display: none;
}
.wf-node:hover {
  border-color: #1677ff;
}
.wf-node.selected {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.18);
}
.wf-node.govern {
  border-color: #d48806;
}
.wf-node.govern::after {
  background: #d48806;
}
.wf-node.query {
  border-color: #389e0d;
}
.wf-node.query::before {
  background: #389e0d;
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
  line-height: 1.4;
  color: rgba(0, 0, 0, 0.88);
}
.wf-node .nd {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 8px;
  line-height: 1.4;
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
  height: 56px;
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
.wf-flow {
  display: flex;
}
.wf-arrow {
  display: none;
}
.wf-row,
.wf-edge {
  display: none;
}
.detail-body {
  padding: 10px 12px;
}
.detail-meta {
  display: grid;
  gap: 6px;
  font-size: 12px;
  margin-bottom: 10px;
  color: rgba(0, 0, 0, 0.75);
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
  max-height: calc(100% - 80px);
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
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
.console-resizer:hover,
.console-resizer:active {
  background: rgba(22, 119, 255, 0.25);
}
.console-hd {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
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
  font-weight: 500;
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
  padding: 8px 0;
}
.result-body {
  padding: 8px;
}
.log-line {
  padding: 2px 0;
  color: rgba(0, 0, 0, 0.65);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.log-line.ok {
  color: #389e0d;
}
.log-line.fail {
  color: #cf1322;
}
</style>

<style>
.ad-ctx-mask {
  position: fixed;
  inset: 0;
  z-index: 1100;
}
.ad-ctx-menu {
  position: fixed;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  min-width: 140px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  border: 1px solid #f0f0f0;
}
.ad-ctx-menu li {
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.88);
}
.ad-ctx-menu li:hover {
  background: #f5f5f5;
}
.ad-ctx-menu li.danger {
  color: #ff4d4f;
}
</style>
