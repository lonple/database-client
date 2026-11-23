<template>
  <div class="page">
    <div class="bar">
      <a-space>
        <a-button @click="goSpace">返回测评空间</a-button>
        <span>测评任务</span>
      </a-space>
      <a-button @click="load">刷新</a-button>
    </div>
    <a-table
      row-key="id"
      size="middle"
      :loading="loading"
      :data-source="tasks"
      :columns="columns"
      :pagination="false"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
        </template>
        <template v-else-if="column.key === 'metrics'">
          <span v-if="record.metrics">
            pass {{ record.metrics.exactPass ?? 0 }}/{{ record.metrics.total ?? 0 }}
            · tables {{ record.metrics.tableSelectOk ?? 0 }}/{{ record.metrics.tableSelectScored ?? 0 }}
            · failAsk {{ record.metrics.askFailed ?? 0 }}
          </span>
          <span v-else>-</span>
        </template>
        <template v-else-if="column.key === 'elapsed'">
          {{ formatElapsed(record.elapsedMs ?? record.metrics?.elapsedMs) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="goDetail(record.id)">详情</a-button>
            <a-button type="link" size="small" @click="openRename(record)">重命名</a-button>
            <a-button
              v-if="record.status === 'PENDING' || record.status === 'CANCELLED'"
              type="link"
              size="small"
              @click="onStart(record.id)"
            >
              启动
            </a-button>
            <a-button
              v-if="record.status === 'RUNNING' || record.status === 'PENDING'"
              type="link"
              danger
              size="small"
              @click="onCancel(record.id)"
            >
              取消
            </a-button>
            <a-button
              v-if="record.status !== 'RUNNING'"
              type="link"
              danger
              size="small"
              @click="onDelete(record)"
            >
              删除
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="renameOpen"
      title="修改任务名称"
      ok-text="保存"
      :confirm-loading="renameSaving"
      @ok="onRenameOk"
    >
      <a-input
        v-model:value="renameName"
        :maxlength="128"
        allow-clear
        placeholder="请输入任务名称"
        @pressEnter="onRenameOk"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import * as evalApi from '@/modules/askdata/api/eval'
import type { EvalTask } from '@/modules/askdata/api/eval'

const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => Number(route.params.workspaceId))
const projectId = computed(() =>
  route.query.projectId ? Number(route.query.projectId) : undefined,
)

const loading = ref(false)
const tasks = ref<EvalTask[]>([])
const renameOpen = ref(false)
const renameName = ref('')
const renameSaving = ref(false)
const renamingTask = ref<EvalTask | null>(null)

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '工程', dataIndex: 'projectId', key: 'projectId', width: 90 },
  { title: '状态', key: 'status', width: 120 },
  { title: '指标', key: 'metrics' },
  { title: '耗时', key: 'elapsed', width: 100 },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: '操作', key: 'action', width: 280 },
]

function formatElapsed(ms?: number | null) {
  if (ms == null || Number.isNaN(ms)) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s % 60)
  return `${m}m ${String(rem).padStart(2, '0')}s`
}

function statusColor(s: string) {
  if (s === 'SUCCEEDED') return 'green'
  if (s === 'RUNNING') return 'blue'
  if (s === 'FAILED') return 'red'
  if (s === 'CANCELLED') return 'orange'
  return 'default'
}

async function load() {
  loading.value = true
  try {
    const resp = await evalApi.listEvalTasks({
      workspaceId: workspaceId.value,
      projectId: projectId.value,
    })
    tasks.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载任务失败')
  } finally {
    loading.value = false
  }
}

async function onStart(id: number) {
  try {
    await evalApi.startEvalTask(id)
    message.success('已启动')
    await load()
  } catch (e: any) {
    message.error(e?.message || '启动失败')
  }
}

async function onCancel(id: number) {
  try {
    await evalApi.cancelEvalTask(id)
    message.success('已请求取消')
    await load()
  } catch (e: any) {
    message.error(e?.message || '取消失败')
  }
}

function openRename(row: EvalTask) {
  renamingTask.value = row
  renameName.value = row.name || ''
  renameOpen.value = true
}

async function onRenameOk() {
  const row = renamingTask.value
  if (!row) return
  const name = renameName.value.trim()
  if (!name) {
    message.warning('任务名称不能为空')
    return Promise.reject()
  }
  if (name === row.name) {
    renameOpen.value = false
    return
  }
  renameSaving.value = true
  try {
    const resp = await evalApi.patchEvalTask(row.id, { name })
    const idx = tasks.value.findIndex((t) => t.id === row.id)
    if (idx >= 0) {
      tasks.value[idx] = { ...tasks.value[idx], ...(resp.data || {}), name }
    }
    message.success('任务名称已更新')
    renameOpen.value = false
  } catch (e: any) {
    message.error(e?.message || '修改失败')
    return Promise.reject(e)
  } finally {
    renameSaving.value = false
  }
}

function onDelete(row: EvalTask) {
  Modal.confirm({
    title: '删除测评任务',
    content: `确认删除「${row.name}」？用例跑批记录将一并删除。`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await evalApi.deleteEvalTask(row.id)
        message.success('已删除')
        await load()
      } catch (e: any) {
        message.error(e?.message || '删除失败')
        throw e
      }
    },
  })
}

function goDetail(id: number) {
  router.push({
    name: 'askdata-eval-task-detail',
    params: { workspaceId: String(workspaceId.value), taskId: String(id) },
  })
}

function goSpace() {
  router.push({
    name: 'askdata-eval',
    params: { workspaceId: String(workspaceId.value) },
  })
}

onMounted(load)
</script>

<style scoped>
.page {
  padding: 16px 20px;
  height: 100%;
  overflow: auto;
  background: #f5f5f5;
}
.bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}
</style>
