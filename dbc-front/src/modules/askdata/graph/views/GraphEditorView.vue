<template>
  <div class="editor">
    <header class="bar">
      <div class="left">
        <a-button type="link" @click="router.push({ name: 'askdata-table-relations' })">← 返回</a-button>
        <strong>{{ canvas?.name || '加载中…' }}</strong>
        <span class="save" :class="saveState">{{ saveLabel }}</span>
      </div>
      <a-space>
        <a-button danger :disabled="!selection" @click="removeSelected">删除选中</a-button>
        <a-button @click="fitView">适应画布</a-button>
      </a-space>
    </header>

    <div class="body">
      <aside class="toolbar">
        <div class="tool-title">工具</div>
        <div
          class="tool-item"
          draggable="true"
          title="拖到画布创建实体"
          @dragstart="onToolDragStart"
        >
          <div class="entity-preview">实体</div>
          <div class="tool-cap">实体框</div>
        </div>
        <p class="tool-tip">拖到画布放置；从实体右侧圆点拖到另一实体左侧圆点连线。</p>
      </aside>

      <div class="canvas-wrap">
        <div v-if="loading" class="canvas-loading">
          <a-spin />
        </div>
        <GraphCanvas
          v-if="canvas"
          ref="canvasRef"
          class="flow-fill"
          v-model:nodes="vfNodes"
          v-model:edges="vfEdges"
          @connect="onConnect"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="clearSelection"
          @node-drag-stop="onDragStop"
          @drop-entity="onDropEntity"
        />
      </div>

      <aside class="inspector">
        <template v-if="selectedNode && editingNode">
          <h3>实体属性</h3>
          <a-form layout="vertical">
            <a-form-item label="名称"><a-input v-model:value="nodeForm.name" /></a-form-item>
            <a-form-item label="类型"><a-input v-model:value="nodeForm.nodeType" placeholder="如 人物" /></a-form-item>
            <a-form-item label="性别">
              <a-select v-model:value="nodeForm.gender" allow-clear placeholder="可选" style="width:100%">
                <a-select-option value="男">男</a-select-option>
                <a-select-option value="女">女</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="描述"><a-textarea v-model:value="nodeForm.description" :rows="3" /></a-form-item>
            <a-form-item label="扩展属性 JSON">
              <a-textarea v-model:value="nodeForm.propsJson" :rows="5" placeholder='不含 gender，性别用上方字段' />
            </a-form-item>
            <a-space>
              <a-button type="primary" @click="applyNode">保存</a-button>
              <a-button @click="editingNode = false">取消</a-button>
            </a-space>
          </a-form>
        </template>
        <template v-else-if="selectedNode">
          <h3>实体</h3>
          <div class="kv"><span>名称</span><b>{{ selectedNode.name }}</b></div>
          <div class="kv"><span>类型</span>{{ selectedNode.nodeType || '—' }}</div>
          <div class="kv"><span>性别</span>{{ nodeGender(selectedNode) || '—' }}</div>
          <div class="kv"><span>描述</span>{{ selectedNode.description || '—' }}</div>
          <pre v-if="propsWithoutGender(selectedNode).length" class="props">{{ propsWithoutGender(selectedNode) }}</pre>
          <a-button type="primary" style="margin-top:12px" @click="startEditNode">编辑属性</a-button>
        </template>
        <template v-else-if="selectedEdge && editingEdge">
          <h3>关系属性</h3>
          <div class="dir">{{ edgeFromName }} → {{ edgeToName }}</div>
          <a-form layout="vertical">
            <a-form-item label="关系类型"><a-input v-model:value="edgeForm.relType" /></a-form-item>
            <a-form-item label="说明"><a-textarea v-model:value="edgeForm.description" :rows="3" /></a-form-item>
            <a-space>
              <a-button type="primary" @click="applyEdge">保存</a-button>
              <a-button @click="editingEdge = false">取消</a-button>
            </a-space>
          </a-form>
        </template>
        <template v-else-if="selectedEdge">
          <h3>关系线</h3>
          <div class="dir">{{ edgeFromName }} → {{ edgeToName }}</div>
          <div class="kv"><span>类型</span><b>{{ selectedEdge.relType }}</b></div>
          <div class="kv"><span>说明</span>{{ selectedEdge.description || '—' }}</div>
          <a-button type="primary" style="margin-top:12px" @click="startEditEdge">编辑属性</a-button>
        </template>
        <div v-else class="hint">选中实体或关系线查看属性；同向可建多条关系线。</div>
      </aside>
    </div>

    <a-modal v-model:open="edgeModalOpen" title="创建关系" @ok="submitEdge" ok-text="创建">
      <div class="dir" style="margin-bottom:12px">{{ pendingFromName }} → {{ pendingToName }}</div>
      <a-form layout="vertical">
        <a-form-item label="关系类型" required>
          <a-input v-model:value="pendingRelType" placeholder="如 配偶、父母、依赖" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="pendingRelDesc" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import type { Edge, Node } from '@vue-flow/core'
import GraphCanvas from '../components/GraphCanvas.vue'
import { graphApi, type CanvasData, type GraphEdge, type GraphNode } from '../../api/graph'
import { mapCanvasToFlow } from '../utils/canvasMap'

const route = useRoute()
const router = useRouter()
const graphId = computed(() => Number(route.params.graphId))
const canvas = ref<CanvasData | null>(null)
const loading = ref(false)
const saveState = ref<'idle' | 'saving' | 'error'>('idle')
const saveLabel = computed(() =>
  saveState.value === 'saving' ? '保存中…' : saveState.value === 'error' ? '保存失败' : '已保存',
)

const vfNodes = ref<Node[]>([])
const vfEdges = ref<Edge[]>([])
const canvasRef = ref<{ fitView: () => void } | null>(null)

const selectedNode = ref<GraphNode | null>(null)
const selectedEdge = ref<GraphEdge | null>(null)
const editingNode = ref(false)
const editingEdge = ref(false)
const selection = computed(() => selectedNode.value || selectedEdge.value)

const nodeForm = reactive({ name: '', nodeType: '', gender: undefined as string | undefined, description: '', propsJson: '{}' })
const edgeForm = reactive({ relType: '', description: '' })

function nodeGender(n: GraphNode): string {
  return (n.gender || (n.props?.gender as string) || '').trim()
}

function stripGenderProps(props?: Record<string, unknown>): Record<string, unknown> {
  const p = { ...(props || {}) }
  delete p.gender
  return p
}

function propsWithoutGender(n: GraphNode): string {
  const p = stripGenderProps(n.props)
  return Object.keys(p).length ? JSON.stringify(p, null, 2) : ''
}

function fillNodeForm(n: GraphNode) {
  nodeForm.name = n.name
  nodeForm.nodeType = n.nodeType || ''
  nodeForm.gender = nodeGender(n) || undefined
  nodeForm.description = n.description || ''
  nodeForm.propsJson = JSON.stringify(stripGenderProps(n.props), null, 2)
}

const edgeModalOpen = ref(false)
const pendingFrom = ref('')
const pendingTo = ref('')
const pendingRelType = ref('')
const pendingRelDesc = ref('')
let posTimer: number | undefined

const nodeNameMap = computed(() => {
  const m = new Map<string, string>()
  for (const n of canvas.value?.nodes || []) m.set(n.nodeId, n.name)
  return m
})
const edgeFromName = computed(() => nodeNameMap.value.get(selectedEdge.value?.fromNodeId || '') || '')
const edgeToName = computed(() => nodeNameMap.value.get(selectedEdge.value?.toNodeId || '') || '')
const pendingFromName = computed(() => nodeNameMap.value.get(pendingFrom.value) || pendingFrom.value)
const pendingToName = computed(() => nodeNameMap.value.get(pendingTo.value) || pendingTo.value)

function toVf(data: CanvasData) {
  const mapped = mapCanvasToFlow(data)
  vfNodes.value = mapped.nodes
  vfEdges.value = mapped.edges
}

function findGraphNode(id: string | undefined): GraphNode | undefined {
  if (!id) return undefined
  const fromCanvas = canvas.value?.nodes.find((n) => n.nodeId === id)
  if (fromCanvas) return fromCanvas
  const flow = vfNodes.value as Array<{ id: string; data?: GraphNode }>
  return flow.find((n) => n.id === id)?.data
}

function findGraphEdge(id: string | undefined): GraphEdge | undefined {
  if (!id) return undefined
  return canvas.value?.edges.find((e) => e.edgeId === id)
}

async function load() {
  loading.value = true
  try {
    canvas.value = await graphApi.getCanvas(graphId.value)
    toVf(canvas.value)
  } finally {
    loading.value = false
  }
}

function onToolDragStart(ev: DragEvent) {
  ev.dataTransfer?.setData('application/ada-graph-tool', 'entity')
  ev.dataTransfer?.setData('text/plain', 'entity')
  ev.dataTransfer!.effectAllowed = 'copy'
}

async function onDropEntity(pos: { x: number; y: number }) {
  saveState.value = 'saving'
  try {
    const n = await graphApi.createNode(graphId.value, {
      name: '新实体',
      nodeType: '实体',
      x: pos.x,
      y: pos.y,
    })
    canvas.value!.nodes.push(n)
    toVf(canvas.value!)
    selectNode(n)
    editingNode.value = true
    saveState.value = 'idle'
  } catch {
    saveState.value = 'error'
  }
}

function onNodeClick(node: Node) {
  const raw = findGraphNode(node.id)
  if (raw) selectNode(raw)
}

function onEdgeClick(edge: Edge) {
  const raw = findGraphEdge(edge.id)
  if (!raw) return
  selectedNode.value = null
  editingNode.value = false
  selectedEdge.value = raw
  editingEdge.value = false
  edgeForm.relType = raw.relType
  edgeForm.description = raw.description || ''
}

function selectNode(n: GraphNode) {
  selectedEdge.value = null
  editingEdge.value = false
  selectedNode.value = n
  editingNode.value = false
  fillNodeForm(n)
}

function startEditNode() {
  if (!selectedNode.value) return
  fillNodeForm(selectedNode.value)
  editingNode.value = true
}

function startEditEdge() {
  if (!selectedEdge.value) return
  edgeForm.relType = selectedEdge.value.relType
  edgeForm.description = selectedEdge.value.description || ''
  editingEdge.value = true
}

function clearSelection() {
  selectedNode.value = null
  selectedEdge.value = null
  editingNode.value = false
  editingEdge.value = false
}

async function applyNode() {
  if (!selectedNode.value) return
  let props: Record<string, unknown> = {}
  try {
    props = nodeForm.propsJson.trim() ? JSON.parse(nodeForm.propsJson) : {}
  } catch {
    message.error('扩展属性 JSON 不合法')
    return
  }
  props = stripGenderProps(props)
  if (!nodeForm.name.trim()) {
    message.warning('名称不能为空')
    return
  }
  saveState.value = 'saving'
  try {
    const updated = await graphApi.updateNode(graphId.value, selectedNode.value.nodeId, {
      name: nodeForm.name.trim(),
      nodeType: nodeForm.nodeType,
      gender: nodeForm.gender || '',
      description: nodeForm.description,
      props,
    })
    const i = canvas.value!.nodes.findIndex((n) => n.nodeId === updated.nodeId)
    if (i >= 0) canvas.value!.nodes[i] = { ...canvas.value!.nodes[i], ...updated }
    toVf(canvas.value!)
    selectNode(canvas.value!.nodes[i])
    editingNode.value = false
    saveState.value = 'idle'
  } catch {
    saveState.value = 'error'
  }
}

async function applyEdge() {
  if (!selectedEdge.value) return
  if (!edgeForm.relType.trim()) {
    message.warning('关系类型不能为空')
    return
  }
  saveState.value = 'saving'
  try {
    const updated = await graphApi.updateEdge(graphId.value, selectedEdge.value.edgeId, {
      relType: edgeForm.relType.trim(),
      description: edgeForm.description,
    })
    const i = canvas.value!.edges.findIndex((e) => e.edgeId === updated.edgeId)
    if (i >= 0) canvas.value!.edges[i] = updated
    toVf(canvas.value!)
    selectedEdge.value = updated
    editingEdge.value = false
    saveState.value = 'idle'
  } catch {
    saveState.value = 'error'
  }
}

function onConnect(conn: { source: string; target: string }) {
  pendingFrom.value = conn.source
  pendingTo.value = conn.target
  pendingRelType.value = ''
  pendingRelDesc.value = ''
  edgeModalOpen.value = true
}

async function submitEdge() {
  if (!pendingRelType.value.trim()) {
    message.warning('关系类型必填')
    return
  }
  saveState.value = 'saving'
  try {
    const e = await graphApi.createEdge(graphId.value, {
      fromNodeId: pendingFrom.value,
      toNodeId: pendingTo.value,
      relType: pendingRelType.value.trim(),
      description: pendingRelDesc.value,
    })
    canvas.value!.edges.push(e)
    toVf(canvas.value!)
    edgeModalOpen.value = false
    selectedEdge.value = e
    editingEdge.value = false
    saveState.value = 'idle'
  } catch {
    saveState.value = 'error'
  }
}

function onDragStop(node: Node) {
  window.clearTimeout(posTimer)
  posTimer = window.setTimeout(async () => {
    saveState.value = 'saving'
    try {
      await graphApi.updatePosition(graphId.value, node.id, node.position.x, node.position.y)
      const raw = canvas.value?.nodes.find((n) => n.nodeId === node.id)
      if (raw) {
        raw.x = node.position.x
        raw.y = node.position.y
      }
      saveState.value = 'idle'
    } catch {
      saveState.value = 'error'
    }
  }, 400)
}

function removeSelected() {
  if (selectedNode.value) {
    const n = selectedNode.value
    Modal.confirm({
      title: `删除实体「${n.name}」？`,
      content: '将同时删除相连关系线。',
      async onOk() {
        await graphApi.deleteNode(graphId.value, n.nodeId)
        await load()
        clearSelection()
      },
    })
  } else if (selectedEdge.value) {
    const e = selectedEdge.value
    Modal.confirm({
      title: '删除这条关系线？',
      async onOk() {
        await graphApi.deleteEdge(graphId.value, e.edgeId)
        await load()
        clearSelection()
      },
    })
  }
}

function fitView() {
  canvasRef.value?.fitView()
}

onMounted(load)
</script>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
}
.bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0 8px;
  flex-shrink: 0;
}
.left { display: flex; align-items: center; gap: 8px; }
.save { font-size: 12px; color: #52c41a; }
.save.saving { color: #1677ff; }
.save.error { color: #ff4d4f; }
.body {
  flex: 1;
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr) 300px;
  gap: 12px;
  min-height: 0;
}
.toolbar {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}
.tool-title { font-weight: 600; margin-bottom: 10px; }
.tool-item {
  border: 1px dashed #91caff;
  border-radius: 8px;
  padding: 10px 8px;
  text-align: center;
  cursor: grab;
  background: #f0f5ff;
  user-select: none;
}
.tool-item:active { cursor: grabbing; }
.entity-preview {
  margin: 0 auto 6px;
  width: 72px;
  padding: 8px;
  border: 1.5px solid #91caff;
  border-radius: 6px;
  background: #e6f4ff;
  font-weight: 600;
  font-size: 12px;
}
.tool-cap { font-size: 12px; color: #1677ff; }
.tool-tip { margin-top: 12px; font-size: 11px; color: #999; line-height: 1.5; }
.canvas-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  height: 100%;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}
.canvas-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
}
.flow-fill {
  position: absolute;
  inset: 0;
}
.inspector {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
  overflow: auto;
}
.hint { color: #999; line-height: 1.6; }
.dir { color: #666; margin-bottom: 10px; }
.kv { margin-bottom: 8px; font-size: 13px; color: #595959; }
.kv span { display: inline-block; width: 48px; color: #8c8c8c; }
.kv b { color: #1f1f1f; }
.props {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 8px;
  font-size: 12px;
  max-height: 160px;
  overflow: auto;
}
</style>
