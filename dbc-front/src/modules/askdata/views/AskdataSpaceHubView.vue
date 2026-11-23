<template>
  <div class="space-hub">
    <div class="hub-bar">
      <div>
        <h2>问数空间</h2>
        <p class="hint">选择工作空间后，进入问数工作台或测评空间。</p>
      </div>
      <a-select
        v-model:value="selectedId"
        show-search
        allow-clear
        placeholder="选择工作空间"
        style="width: 320px"
        :loading="listLoading"
        :options="wsOptions"
        :filter-option="filterOption"
      />
    </div>
    <div class="hub-body">
      <a-empty v-if="!selectedId" description="请先在上方选择工作空间" />
      <div v-else class="entry-grid">
        <div class="entry-card">
          <h3>工作空间</h3>
          <p>自然语言生成工作流；人工确认保存与执行；适合日常探索。</p>
          <a-button type="primary" size="large" @click="enterWorkbench">进入工作空间</a-button>
        </div>
        <div class="entry-card">
          <h3>测评空间</h3>
          <p>引用模板用例、自定义用例、创建测评任务；自动跑批比对正确率。</p>
          <a-button type="primary" size="large" @click="enterEval">进入测评空间</a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { listMyWorkspaces, type WorkspaceSummary } from '@/modules/sqlwork/api/sqlwork'

const router = useRouter()
const workspaces = ref<WorkspaceSummary[]>([])
const listLoading = ref(false)
const selectedId = ref<number | null>(null)

const wsOptions = computed(() =>
  workspaces.value.map((w) => ({ label: w.name, value: w.id })),
)

function filterOption(input: string, option?: { label?: string }) {
  return (option?.label || '').toLowerCase().includes(input.toLowerCase())
}

async function load() {
  listLoading.value = true
  try {
    const resp = await listMyWorkspaces()
    workspaces.value = resp.data || []
    if (!selectedId.value && workspaces.value.length === 1) {
      selectedId.value = workspaces.value[0].id
    }
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
.space-hub {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px 28px;
  overflow: auto;
}
.hub-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
}
.hub-bar h2 {
  margin: 0 0 6px;
  font-size: 20px;
}
.hint {
  margin: 0;
  color: #8c8c8c;
  font-size: 13px;
}
.hub-body {
  flex: 1;
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
