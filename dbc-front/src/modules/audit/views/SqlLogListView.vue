<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>审计日志</a-breadcrumb-item>
      <a-breadcrumb-item>SQL 操作日志</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>SQL 操作日志</h2>
    </div>
    <a-form layout="inline" class="filter-row" @finish="onSearch">
      <a-form-item label="操作人">
        <a-input v-model:value="query.operatorUsername" allow-clear placeholder="用户名" style="width: 140px" />
      </a-form-item>
      <a-form-item label="状态">
        <a-select v-model:value="query.status" allow-clear placeholder="全部" style="width: 120px"
          :options="[
            { value: 'SUCCESS', label: '成功' },
            { value: 'FAIL', label: '失败' },
          ]"
        />
      </a-form-item>
      <a-form-item label="SQL">
        <a-input v-model:value="query.sqlKeyword" allow-clear placeholder="关键字" style="width: 200px" />
      </a-form-item>
      <a-form-item>
        <a-space>
          <a-button type="primary" html-type="submit" :loading="loading">查询</a-button>
          <a-button @click="onReset">重置</a-button>
        </a-space>
      </a-form-item>
    </a-form>
    <a-table
      row-key="eventId"
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'occurredAt'">
          {{ formatTime(record.occurredAt) }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 'SUCCESS' ? 'success' : 'error'">
            {{ record.status === 'SUCCESS' ? '成功' : '失败' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'sqlText'">
          <span class="sql-preview" :title="record.sqlText">{{ preview(record.sqlText) }}</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <a @click="openDetail(record.eventId)">详情</a>
        </template>
      </template>
    </a-table>

    <a-drawer v-model:open="detailOpen" title="SQL 审计详情" width="720" destroy-on-close>
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="时间">{{ formatTime(detail.occurredAt) }}</a-descriptions-item>
            <a-descriptions-item label="操作人">{{ detail.operatorUsername }}</a-descriptions-item>
            <a-descriptions-item label="IP">{{ detail.clientIp || '-' }}</a-descriptions-item>
            <a-descriptions-item label="工作空间">
              {{ detail.workspaceName || detail.workspaceId || '-' }}
            </a-descriptions-item>
            <a-descriptions-item label="连接">
              {{ detail.connectionName || detail.connectionId || '-' }}
            </a-descriptions-item>
            <a-descriptions-item label="库类型">{{ detail.dbType || '-' }}</a-descriptions-item>
            <a-descriptions-item label="语句类型">{{ detail.statementType || '-' }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="detail.status === 'SUCCESS' ? 'success' : 'error'">
                {{ detail.status === 'SUCCESS' ? '成功' : (detail.status || '-') }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="耗时">{{ detail.elapsedMs ?? '-' }} ms</a-descriptions-item>
            <a-descriptions-item label="批次">{{ detail.batchId }} #{{ detail.statementIndex }}</a-descriptions-item>
            <a-descriptions-item v-if="detail.sqlTruncated" label="截断">
              正文已因安全上限截断
            </a-descriptions-item>
          </a-descriptions>
          <h4 class="block-title">SQL</h4>
          <pre class="sql-block">{{ detail.sqlText }}</pre>
          <template v-if="detail.failDetail">
            <h4 class="block-title">失败详情</h4>
            <ReadableKvPanel :data="detail.failDetail" />
          </template>
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { TablePaginationConfig } from 'ant-design-vue'
import * as auditApi from '@/modules/audit/api/audit'
import type { SqlAuditLog } from '@/modules/audit/api/audit'
import ReadableKvPanel from '@/modules/audit/components/ReadableKvPanel.vue'

const loading = ref(false)
const rows = ref<SqlAuditLog[]>([])
const query = reactive({
  operatorUsername: '',
  status: undefined as string | undefined,
  sqlKeyword: '',
})
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (t: number) => `共 ${t} 条`,
})

const columns = [
  { title: '时间', dataIndex: 'occurredAt', key: 'occurredAt', width: 180 },
  { title: '操作人', dataIndex: 'operatorUsername', key: 'operatorUsername', width: 120 },
  { title: '连接', dataIndex: 'connectionName', key: 'connectionName', width: 140 },
  { title: '类型', dataIndex: 'statementType', key: 'statementType', width: 100 },
  { title: '状态', key: 'status', width: 90 },
  { title: '耗时(ms)', dataIndex: 'elapsedMs', key: 'elapsedMs', width: 90 },
  { title: 'SQL', key: 'sqlText', ellipsis: true },
  { title: '操作', key: 'action', width: 80 },
]

const detailOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<SqlAuditLog | null>(null)

function preview(sql?: string) {
  if (!sql) return ''
  const one = sql.replace(/\s+/g, ' ').trim()
  return one.length > 120 ? one.slice(0, 120) + '…' : one
}

function formatTime(v?: string) {
  if (!v) return '-'
  try {
    return new Date(v).toLocaleString()
  } catch {
    return v
  }
}

async function load() {
  loading.value = true
  try {
    const resp = await auditApi.fetchSqlLogs({
      page: pagination.current,
      size: pagination.pageSize,
      operatorUsername: query.operatorUsername || undefined,
      status: query.status,
      sqlKeyword: query.sqlKeyword || undefined,
    })
    rows.value = resp.data?.records || []
    pagination.total = Number(resp.data?.total || 0)
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.current = 1
  load()
}

function onReset() {
  query.operatorUsername = ''
  query.status = undefined
  query.sqlKeyword = ''
  pagination.current = 1
  load()
}

function onTableChange(pag: TablePaginationConfig) {
  pagination.current = Number(pag.current || 1)
  pagination.pageSize = Number(pag.pageSize || 20)
  load()
}

async function openDetail(eventId: string) {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const resp = await auditApi.fetchSqlLogDetail(eventId)
    detail.value = resp.data
  } finally {
    detailLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.title-row h2 {
  margin: 0;
  font-size: 18px;
}
.filter-row {
  margin-bottom: 12px;
}
.sql-preview {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
}
.block-title {
  margin: 16px 0 8px;
}
.sql-block {
  margin: 0;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  max-height: 360px;
  overflow: auto;
}
</style>
