<template>
  <div class="askdata-shell">
    <aside class="shell-side">
      <div class="shell-brand">智能问数</div>
      <a-menu
        mode="inline"
        :selected-keys="[selectedKey]"
        :items="menuItems"
        @click="onMenu"
      />
    </aside>
    <main class="shell-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MenuProps } from 'ant-design-vue'
import {
  AppstoreOutlined,
  BookOutlined,
  FileTextOutlined,
  PartitionOutlined,
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()

const menuItems: MenuProps['items'] = [
  {
    key: 'spaces',
    icon: () => h(AppstoreOutlined),
    label: '问数空间',
  },
  {
    key: 'knowledge',
    icon: () => h(BookOutlined),
    label: '知识库',
  },
  {
    key: 'documents',
    icon: () => h(FileTextOutlined),
    label: '文档管理',
  },
  {
    key: 'table-relations',
    icon: () => h(PartitionOutlined),
    label: '库表关系',
  },
]

const selectedKey = computed(() => {
  const name = String(route.name || '')
  if (name.startsWith('askdata-knowledge')) return 'knowledge'
  if (name.startsWith('askdata-document')) return 'documents'
  if (name.startsWith('askdata-table-relation') || name.startsWith('askdata-graph')) return 'table-relations'
  return 'spaces'
})

function onMenu(info: { key: string | number }) {
  const key = String(info.key)
  if (key === 'knowledge') {
    router.push({ name: 'askdata-knowledge' })
  } else if (key === 'documents') {
    router.push({ name: 'askdata-documents' })
  } else if (key === 'table-relations') {
    router.push({ name: 'askdata-table-relations' })
  } else {
    router.push({ name: 'askdata-spaces' })
  }
}
</script>

<style scoped>
.askdata-shell {
  display: flex;
  height: 100%;
  background: #f5f5f5;
}
.shell-side {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}
.shell-brand {
  padding: 16px 20px 12px;
  font-weight: 600;
  font-size: 15px;
  border-bottom: 1px solid #f0f0f0;
}
.shell-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.shell-main > :deep(*) {
  flex: 1;
  min-height: 0;
}
</style>
