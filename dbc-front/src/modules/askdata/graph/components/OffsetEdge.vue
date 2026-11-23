<template>
  <BaseEdge
    :id="id"
    :path="edgePath"
    :marker-end="markerEnd"
    :style="edgeStyle"
    :interaction-width="24"
  />
  <EdgeLabelRenderer v-if="label">
    <div
      class="edge-label nodrag nopan"
      :style="{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }"
    >
      {{ label }}
    </div>
  </EdgeLabelRenderer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@vue-flow/core'

const props = defineProps<EdgeProps>()

const pathInfo = computed(() => {
  const idx = Number(props.data?.parallelIndex || 0)
  const curvature = 0.22 + idx * 0.2
  return getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition,
    curvature,
  })
})

const edgePath = computed(() => pathInfo.value[0])
const labelX = computed(() => pathInfo.value[1])
const labelY = computed(() => pathInfo.value[2])
const edgeStyle = computed(() => ({
  ...(typeof props.style === 'object' && props.style ? props.style : {}),
  strokeWidth: props.selected ? 3 : 2,
}))
</script>

<style scoped>
.edge-label {
  position: absolute;
  font-size: 11px;
  color: #595959;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 1px 6px;
  pointer-events: none;
}
</style>
