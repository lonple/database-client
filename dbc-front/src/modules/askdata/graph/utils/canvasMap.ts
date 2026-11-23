import type { Edge, Node } from '@vue-flow/core'
import type { CanvasData } from '../../api/graph'

export function mapCanvasToFlow(data: CanvasData, opts?: { readonly?: boolean }): { nodes: Node[]; edges: Edge[] } {
  const readonly = !!opts?.readonly
  const parallel = new Map<string, number>()
  const nodes: Node[] = data.nodes.map((n) => {
    const female = (n.gender || n.props?.gender) === '女'
    return {
      id: n.nodeId,
      type: 'entity',
      position: { x: n.x, y: n.y },
      data: { ...n },
      draggable: !readonly,
      connectable: !readonly,
      style: female ? { background: '#fff0f6', borderColor: '#ffadd2' } : undefined,
    }
  })
  const edges: Edge[] = data.edges.map((e) => {
    const key = `${e.fromNodeId}->${e.toNodeId}`
    const idx = parallel.get(key) || 0
    parallel.set(key, idx + 1)
    return {
      id: e.edgeId,
      type: 'offset',
      source: e.fromNodeId,
      target: e.toNodeId,
      sourceHandle: 'source',
      targetHandle: 'target',
      label: e.relType,
      data: { ...e, parallelIndex: idx },
      animated: e.relType === '配偶',
      style: { stroke: e.relType === '配偶' ? '#eb2f96' : '#1677ff', strokeWidth: 1.5 },
      selectable: true,
    }
  })
  return { nodes, edges }
}
