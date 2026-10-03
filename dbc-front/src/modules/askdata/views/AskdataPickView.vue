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
        <div class="intro">
          <h2>智能问数</h2>
          <p class="hint">选择后可进入问数工作台，或进入测评空间做回归评测。</p>
        </div>
        <div class="entry-grid">
          <div class="entry-card">
            <h3>问数工作台</h3>
            <p>自然语言生成工作流；人工确认保存与执行；适合日常探索。</p>
            <a-button type="primary" size="large" @click="enterWorkbench">进入工作台</a-button>
          </div>
          <div class="entry-card">
            <h3>测评空间</h3>
            <p>引用模板用例、自定义用例、创建测评任务；自动跑批比对正确率。</p>
            <a-button type="primary" size="large" @click="enterEval">进入测评空间</a-button>
          </div>
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

function enterWorkbench() {
  if (!selectedId.value) return
  router.push({ name: 'askdata-workbench', params: { workspaceId: String(selectedId.value) } })
}

function enterEval() {
  if (!selectedId.value) return
  router.push({ name: 'askdata-eval', params: { workspaceId: String(selectedId.value) } })
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
.ws-item:hover {
  background: #f5f5f5;
}
.ws-item.active {
  background: #e6f4ff;
}
.ws-name {
  font-weight: 500;
}
.pick-main {
  flex: 1;
  padding: 40px 32px;
  overflow: auto;
}
.intro h2 {
  margin: 0 0 8px;
}
.hint {
  color: #8c8c8c;
  margin: 0 0 24px;
}
.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  max-width: 640px;
}
.entry-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 20px 18px;
}
.entry-card h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.entry-card p {
  margin: 0 0 16px;
  color: #8c8c8c;
  font-size: 13px;
  line-height: 1.5;
}
</style>
