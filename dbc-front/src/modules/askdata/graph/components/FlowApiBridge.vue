<template>
  <span class="bridge" aria-hidden="true" />
</template>

<script setup lang="ts">
import { useVueFlow } from '@vue-flow/core'

const props = defineProps<{ flowId: string }>()
const { fitView, screenToFlowCoordinate } = useVueFlow({ id: props.flowId })

defineExpose({
  fitView: (opts?: { padding?: number }) => fitView(opts ?? { padding: 0.2 }),
  screenToFlowCoordinate,
})
</script>

<style scoped>
.bridge { display: none; }
</style>
