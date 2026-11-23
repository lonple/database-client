<template>
  <div class="entity-node" :class="{ selected, female: (data?.gender || data?.props?.gender) === '女' }">
    <Handle
      id="target"
      type="target"
      :position="Position.Left"
      :connectable-start="false"
      :connectable-end="true"
      class="handle"
    />
    <div class="title">{{ data?.name || '实体' }}</div>
    <div v-if="data?.nodeType" class="sub">{{ data.nodeType }}</div>
    <Handle
      id="source"
      type="source"
      :position="Position.Right"
      :connectable-start="true"
      :connectable-end="false"
      class="handle"
    />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'

defineProps<{
  selected?: boolean
  id?: string
  data?: {
    name?: string
    nodeType?: string
    description?: string
    gender?: string
    props?: Record<string, unknown>
  }
}>()
</script>

<style scoped>
.entity-node {
  min-width: 108px;
  padding: 10px 18px;
  border: 1.5px solid #91caff;
  border-radius: 8px;
  background: #e6f4ff;
  font-size: 13px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.entity-node.female {
  background: #fff0f6;
  border-color: #ffadd2;
}
.entity-node.selected {
  border-color: #1677ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.28);
}
.title { font-weight: 600; color: #1f1f1f; user-select: none; }
.sub { margin-top: 2px; font-size: 11px; color: #666; user-select: none; }
.handle {
  width: 12px !important;
  height: 12px !important;
  background: #1677ff !important;
  border: 2px solid #fff !important;
  z-index: 2;
}
</style>
