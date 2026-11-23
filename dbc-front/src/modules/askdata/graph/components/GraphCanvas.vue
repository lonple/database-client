<template>
  <div
    class="canvas-root"
    @dragover.prevent
    @drop="onDrop"
  >
    <VueFlow
      :id="flowId"
      :nodes="nodes"
      :edges="edges"
      :nodes-draggable="!readonly"
      :nodes-connectable="!readonly"
      :elements-selectable="true"
      :edges-updatable="false"
      :connect-on-click="false"
      :connection-mode="ConnectionMode.Loose"
      :connection-radius="24"
      :default-edge-options="{ type: 'offset', markerEnd: MarkerType.ArrowClosed }"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :min-zoom="0.2"
      :max-zoom="2"
      fit-view-on-init
      @update:nodes="onUpdateNodes"
      @update:edges="onUpdateEdges"
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="() => emit('paneClick')"
      @node-drag-stop="onNodeDragStop"
    >
      <Background :gap="16" />
      <Controls />
      <MiniMap v-if="showMinimap" />
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { markRaw, useId } from 'vue'
import {
  VueFlow,
  MarkerType,
  ConnectionMode,
  useVueFlow,
  type Connection,
  type Edge,
  type EdgeMouseEvent,
  type GraphNode,
  type Node,
  type NodeDragEvent,
  type NodeMouseEvent,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import EntityNode from './EntityNode.vue'
import OffsetEdge from './OffsetEdge.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const props = withDefaults(
  defineProps<{
    nodes: Node[]
    edges: Edge[]
    readonly?: boolean
    showMinimap?: boolean
  }>(),
  { readonly: false, showMinimap: true },
)

const emit = defineEmits<{
  'update:nodes': [nodes: Node[]]
  'update:edges': [edges: Edge[]]
  connect: [conn: { source: string; target: string }]
  nodeClick: [node: Node]
  edgeClick: [edge: Edge]
  paneClick: []
  nodeDragStop: [node: Node]
  dropEntity: [pos: { x: number; y: number }]
}>()

const flowId = `gc-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
const nodeTypes = { entity: markRaw(EntityNode) } as any
const edgeTypes = { offset: markRaw(OffsetEdge) } as any

const { screenToFlowCoordinate, fitView } = useVueFlow({ id: flowId })

function onUpdateNodes(next: GraphNode[]) {
  emit('update:nodes', next)
}

function onUpdateEdges(next: Edge[]) {
  emit('update:edges', next)
}

function onConnect(conn: Connection) {
  if (props.readonly) return
  if (conn.source && conn.target && conn.source !== conn.target) {
    emit('connect', { source: conn.source, target: conn.target })
  }
}

function onNodeClick(ev: NodeMouseEvent) {
  emit('nodeClick', ev.node)
}

function onEdgeClick(ev: EdgeMouseEvent) {
  emit('edgeClick', ev.edge)
}

function onNodeDragStop(ev: NodeDragEvent) {
  emit('nodeDragStop', ev.node)
}

function onDrop(ev: DragEvent) {
  if (props.readonly) return
  const kind = ev.dataTransfer?.getData('application/ada-graph-tool')
    || ev.dataTransfer?.getData('text/plain')
  if (kind !== 'entity') return
  ev.preventDefault()
  const pos = screenToFlowCoordinate({ x: ev.clientX, y: ev.clientY })
  emit('dropEntity', { x: pos.x, y: pos.y })
}

defineExpose({
  fitView: () => fitView({ padding: 0.2 }),
})
</script>

<style scoped>
.canvas-root {
  width: 100%;
  height: 100%;
  min-height: 0;
}
:deep(.vue-flow) {
  width: 100%;
  height: 100%;
}
:deep(.vue-flow__container) {
  width: 100%;
  height: 100%;
}
</style>
