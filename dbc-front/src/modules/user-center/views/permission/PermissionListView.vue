<template>
  <div class="perm-page">
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>用户中心</a-breadcrumb-item>
      <a-breadcrumb-item>权限管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <div>
        <h2>权限管理</h2>
        <p class="note">内置权限，仅查看不可编辑。</p>
      </div>
    </div>
    <div class="panels">
      <aside class="module-panel">
        <div
          v-for="m in modules"
          :key="m.moduleCode"
          class="module-item"
          :class="{ active: selectedModule === m.moduleCode }"
          @click="selectedModule = m.moduleCode"
        >
          {{ m.moduleName }}
        </div>
        <a-empty v-if="!modules.length && !loading" description="暂无权限数据" />
      </aside>
      <section class="list-panel">
        <a-table
          row-key="id"
          :columns="columns"
          :data-source="currentPermissions"
          :loading="loading"
          :pagination="false"
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as permApi from '@/modules/user-center/api/permission'
import type { PermissionModuleView } from '@/modules/user-center/api/types'

const loading = ref(false)
const modules = ref<PermissionModuleView[]>([])
const selectedModule = ref<string>('')

const columns = [
  { title: '权限名称', dataIndex: 'name', key: 'name' },
  { title: '权限码', dataIndex: 'code', key: 'code' },
  { title: '权限描述', dataIndex: 'description', key: 'description' },
]

const currentPermissions = computed(() => {
  const m = modules.value.find((x) => x.moduleCode === selectedModule.value)
  return m?.permissions || []
})

onMounted(async () => {
  loading.value = true
  try {
    const resp = await permApi.fetchPermissionModules()
    modules.value = resp.data || []
    selectedModule.value = modules.value[0]?.moduleCode || ''
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.title-row { margin-bottom: 12px; }
.title-row h2 { margin: 0 0 4px; font-size: 20px; }
.note { margin: 0; color: rgba(0,0,0,.45); }
.panels {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  min-height: 480px;
}
.module-panel, .list-panel {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
}
.module-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  color: rgba(0,0,0,.75);
}
.module-item:hover { background: rgba(22,119,255,.06); color: #1677ff; }
.module-item.active {
  background: #e6f4ff;
  color: #1677ff;
  font-weight: 600;
}
</style>
