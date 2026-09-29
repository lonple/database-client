<template>
  <div class="page">
    <div class="hd">
      <h2>智能问数监控</h2>
      <a-space>
        <a-select v-model:value="hours" style="width: 120px" :options="hourOptions" @change="loadSummary" />
        <a-button @click="reload">刷新</a-button>
      </a-space>
    </div>

    <a-row :gutter="12" class="summary">
      <a-col :span="6" v-for="b in summaryBuckets" :key="b.kind + b.status">
        <a-card size="small">
          <div class="card-k">{{ b.kind }} / {{ b.status }}</div>
          <div class="card-v">{{ b.count }}</div>
          <div class="card-s">均延迟 {{ Math.round(b.avgLatencyMs) }} ms</div>
        </a-card>
      </a-col>
    </a-row>

    <a-card title="Span 列表" size="small">
      <a-form layout="inline" class="filters">
        <a-form-item label="kind">
          <a-select v-model:value="filters.kind" allow-clear style="width: 120px" :options="kindOptions" />
        </a-form-item>
        <a-form-item label="status">
          <a-select v-model:value="filters.status" allow-clear style="width: 120px" :options="statusOptions" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="loadSpans">查询</a-button>
        </a-form-item>
      </a-form>
      <a-table
        row-key="id"
        size="middle"
        :loading="loading"
        :columns="columns"
        :data-source="items"
        :pagination="pagination"
        @change="onTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-button type="link" size="small" @click="openDetail(record.id)">详情</a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-drawer v-model:open="detailOpen" title="Span 详情" width="520">
      <pre class="detail">{{ detailJson }}</pre>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as askApi from '@/modules/askdata/api/askdata'

const hours = ref(24)
const hourOptions = [
  { label: '近 24 小时', value: 24 },
  { label: '近 72 小时', value: 72 },
  { label: '近 7 天', value: 168 },
]
const kindOptions = [
  { label: 'LLM', value: 'LLM' },
  { label: 'GRAPH', value: 'GRAPH' },
  { label: 'TOOL', value: 'TOOL' },
  { label: 'HITL', value: 'HITL' },
]
const statusOptions = [
  { label: 'OK', value: 'OK' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CANCELLED', value: 'CANCELLED' },
]

const summaryBuckets = ref<
  Array<{ kind: string; status: string; count: number; avgLatencyMs: number }>
>([])
const loading = ref(false)
const items = ref<askApi.LlmSpanItem[]>([])
const filters = reactive<{ kind?: string; status?: string }>({})
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const detailOpen = ref(false)
const detailJson = ref('')

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
}))

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '时间', dataIndex: 'startedAt', key: 'startedAt', width: 180 },
  { title: 'phase', dataIndex: 'phase', key: 'phase', width: 90 },
  { title: 'kind', dataIndex: 'kind', key: 'kind', width: 90 },
  { title: 'name', dataIndex: 'name', key: 'name' },
  { title: 'status', dataIndex: 'status', key: 'status', width: 100 },
  { title: '延迟(ms)', dataIndex: 'latencyMs', key: 'latencyMs', width: 100 },
  { title: 'model', dataIndex: 'model', key: 'model', width: 120 },
  { title: '操作', key: 'action', width: 80 },
]

async function loadSummary() {
  try {
    const resp = await askApi.fetchLlmSummary(hours.value)
    summaryBuckets.value = resp.data?.buckets || []
  } catch (e: any) {
    message.error(e?.message || '加载汇总失败')
  }
}

async function loadSpans() {
  loading.value = true
  try {
    const resp = await askApi.fetchLlmSpans({
      page: page.value,
      size: pageSize.value,
      kind: filters.kind,
      status: filters.status,
    })
    items.value = resp.data?.items || []
    total.value = resp.data?.total || 0
  } catch (e: any) {
    message.error(e?.message || '加载 span 失败')
  } finally {
    loading.value = false
  }
}

function onTableChange(pag: { current?: number; pageSize?: number }) {
  page.value = pag.current || 1
  pageSize.value = pag.pageSize || 20
  loadSpans()
}

async function openDetail(id: number) {
  try {
    const resp = await askApi.fetchSpanDetail(id)
    detailJson.value = JSON.stringify(resp.data, null, 2)
    detailOpen.value = true
  } catch (e: any) {
    message.error(e?.message || '加载详情失败')
  }
}

function reload() {
  loadSummary()
  loadSpans()
}

onMounted(reload)
</script>

<style scoped>
.page {
  padding: 16px 20px;
}
.hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.hd h2 {
  margin: 0;
  font-size: 18px;
}
.summary {
  margin-bottom: 12px;
}
.card-k {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.card-v {
  font-size: 22px;
  font-weight: 600;
  margin: 4px 0;
}
.card-s {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
.filters {
  margin-bottom: 12px;
}
.detail {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
