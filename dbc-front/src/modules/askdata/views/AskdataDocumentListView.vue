<template>
  <div class="doc-page">
    <div class="doc-bar">
      <div>
        <h2>文档管理</h2>
        <p class="hint">上传 Word / PDF / Excel / HTML / 图片，服务端转为 Markdown。仅本人可见。</p>
      </div>
      <a-space>
        <a-input v-model:value="q" allow-clear placeholder="名称" style="width: 160px" @pressEnter="load" />
        <a-select
          v-model:value="formatFilter"
          allow-clear
          placeholder="格式"
          style="width: 120px"
          :options="formatOptions"
          @change="load"
        />
        <a-select
          v-model:value="statusFilter"
          allow-clear
          placeholder="状态"
          style="width: 120px"
          :options="statusOptions"
          @change="load"
        />
        <a-button @click="load">刷新</a-button>
        <a-button type="primary" @click="openUpload">上传文档</a-button>
      </a-space>
    </div>
    <a-table
      row-key="id"
      size="middle"
      :loading="loading"
      :data-source="rows"
      :columns="columns"
      :pagination="{ pageSize: 20 }"
      :locale="{ emptyText: '暂无文档，请上传 Word、PDF、Excel、HTML 或图片' }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a @click="goDetail(record.id)">{{ record.name }}</a>
        </template>
        <template v-else-if="column.key === 'status'">
          {{ statusLabel(record.convertStatus) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a @click="goDetail(record.id)">详情</a>
        </template>
      </template>
    </a-table>
    <input ref="fileInput" type="file" class="hidden" @change="onPicked" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  listAskDocuments,
  uploadAskDocument,
  type AskDocumentRow,
} from '@/modules/askdata/api/documents'

const router = useRouter()
const loading = ref(false)
const rows = ref<AskDocumentRow[]>([])
const q = ref('')
const formatFilter = ref<string | undefined>()
const statusFilter = ref<string | undefined>()
const fileInput = ref<HTMLInputElement | null>(null)
let timer: number | undefined

const formatOptions = [
  { label: 'docx', value: 'docx' },
  { label: 'pdf', value: 'pdf' },
  { label: 'xlsx', value: 'xlsx' },
  { label: 'html', value: 'html' },
  { label: 'png', value: 'png' },
  { label: 'jpg', value: 'jpg' },
]

const statusOptions = [
  { label: '排队中', value: 'QUEUED' },
  { label: '转换中', value: 'RUNNING' },
  { label: '成功', value: 'SUCCESS' },
  { label: '失败', value: 'FAILED' },
]

const columns = [
  { title: '名称', key: 'name', dataIndex: 'name', ellipsis: true },
  { title: '格式', dataIndex: 'sourceFormat', width: 90 },
  { title: '转换状态', key: 'status', width: 110 },
  { title: '更新时间', dataIndex: 'updatedAt', width: 180 },
  { title: '操作', key: 'action', width: 80 },
]

function statusLabel(v?: string) {
  const s = String(v || '').toUpperCase()
  if (s === 'SUCCESS') return '成功'
  if (s === 'FAILED') return '失败'
  if (s === 'RUNNING') return '转换中'
  if (s === 'QUEUED') return '排队中'
  return v || '—'
}

async function load() {
  loading.value = true
  try {
    const resp = await listAskDocuments({
      q: q.value || undefined,
      sourceFormat: formatFilter.value,
      convertStatus: statusFilter.value,
    })
    rows.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载文档列表失败')
  } finally {
    loading.value = false
  }
}

function goDetail(id: number) {
  router.push({ name: 'askdata-document-detail', params: { id: String(id) } })
}

function openUpload() {
  fileInput.value?.click()
}

async function onPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const resp = await uploadAskDocument(file)
    message.success('已上传，正在转换')
    const id = resp.data?.id
    if (id) goDetail(id)
    else await load()
  } catch (err: any) {
    message.error(err?.message || '上传失败')
  }
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => {
    if (rows.value.some((r) => r.convertStatus === 'QUEUED' || r.convertStatus === 'RUNNING')) {
      void load()
    }
  }, 3000)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.doc-page {
  padding: 20px 24px;
  overflow: auto;
}
.doc-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.doc-bar h2 {
  margin: 0 0 4px;
  font-size: 18px;
}
.hint {
  margin: 0;
  color: #00000073;
  font-size: 13px;
}
.hidden {
  display: none;
}
</style>
