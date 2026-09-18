<template>
  <a-descriptions v-if="items.length" bordered :column="1" size="small">
    <a-descriptions-item v-for="item in items" :key="item.key" :label="item.label">
      {{ item.value }}
    </a-descriptions-item>
  </a-descriptions>
  <a-empty v-else description="无详细内容" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Empty } from 'ant-design-vue'
import { objectEntries } from '@/modules/audit/utils/formatAudit'

const props = defineProps<{
  data?: Record<string, unknown> | null
}>()

const items = computed(() => objectEntries(props.data))
</script>
