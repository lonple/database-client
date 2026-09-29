<template>
  <div class="pick-layout">
    <aside class="pick-side">
      <div class="side-hd">工作空间</div>
      <div class="side-body">
        <a-spin :spinning="listLoading">
          <a-empty v-if="!listLoading && !workspaces.length" description="暂无可用空间" />
          <ul v-else class="ws-list">
            <li
              v-for="w in workspaces"
              :key="w.id"
              class="ws-item"
              :class="{ active: selectedId === w.id }"
              @click="selectedId = w.id"
            >
              <div class="ws-name" :title="w.name">{{ w.name }}</div>
            </li>
          </ul>
        </a-spin>
      </div>
    </aside>
    <main class="pick-main">
      <template v-if="!selectedId">
        <a-empty description="请从左侧选择工作空间" />
      </template>
      <template v-else>
        <div class="panel">
          <h2>智能问数</h2>
          <p class="hint">进入后可创建工程（须指定工作连接），通过对话生成查询工作流并执行。</p>
          <a-button type="primary" size="large" @click="enter">进入问数工作台</a-button>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { listMyWorkspaces, type WorkspaceSummary } from '@/modules/sqlwork/api/sqlwork'

const router = useRouter()
const workspaces = ref<WorkspaceSummary[]>([])
const listLoading = ref(false)
const selectedId = ref<number | null>(null)

async function load() {
  listLoading.value = true
  try {
    const resp = await listMyWorkspaces()
    workspaces.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载工作空间失败')
  } finally {
    listLoading.value = false
  }
}

function enter() {
  if (!selectedId.value) return
  router.push({ name: 'askdata-workbench', params: { workspaceId: String(selectedId.value) } })
}

onMounted(load)
</script>

<style scoped>
.pick-layout {
  display: flex;
  height: calc(100vh - 56px);
  background: #f5f5f5;
}
.pick-side {
  width: 260px;
  background: #fff;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}
.side-hd {
  padding: 14px 16px;
  font-weight: 600;
  border-bottom: 1px solid #f0f0f0;
}
.side-body {
  flex: 1;
  overflow: auto;
  padding: 8px;
}
.ws-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.ws-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.ws-item:hover,
.ws-item.active {
  background: #e6f4ff;
}
.ws-name {
  font-weight: 500;
}
.pick-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.panel {
  text-align: center;
  max-width: 420px;
}
.hint {
  color: rgba(0, 0, 0, 0.45);
  margin: 8px 0 20px;
}
</style>
