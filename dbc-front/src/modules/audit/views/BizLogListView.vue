<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>审计日志</a-breadcrumb-item>
      <a-breadcrumb-item>业务日志</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>业务日志</h2>
    </div>
    <a-form layout="inline" class="filter-row" @finish="onSearch">
      <a-form-item label="操作人">
        <a-input v-model:value="query.operatorUsername" allow-clear placeholder="用户名" style="width: 140px" />
      </a-form-item>
      <a-form-item label="模块">
        <a-input v-model:value="query.module" allow-clear placeholder="如 manage" style="width: 120px" />
      </a-form-item>
      <a-form-item label="动作">
        <a-input v-model:value="query.action" allow-clear placeholder="如 CREATE" style="width: 120px" />
      </a-form-item>
      <a-form-item label="结果">
        <a-select v-model:value="query.result" allow-clear placeholder="全部" style="width: 120px"
          :options="[
            { value: 'SUCCESS', label: '成功' },
            { value: 'FAIL', label: '失败' },
          ]"
        />
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
        <template v-else-if="column.key === 'action'">
          {{ actionLabel(record.action) }}
        </template>
        <template v-else-if="column.key === 'result'">
          <a-tag :color="record.result === 'SUCCESS' ? 'success' : 'error'">
            {{ record.result === 'SUCCESS' ? '成功' : '失败' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'ops'">
          <a @click="openDetail(record.eventId)">详情</a>
        </template>
      </template>
    </a-table>

    <a-drawer v-model:open="detailOpen" title="业务审计详情" width="640" destroy-on-close>
      <a-spin :spinning="detailLoading">
        <template v-if="detail">
          <a-descriptions bordered :column="1" size="small">
            <a-descriptions-item label="时间">{{ formatTime(detail.occurredAt) }}</a-descriptions-item>
            <a-descriptions-item label="操作人">{{ detail.operatorUsername }}</a-descriptions-item>
            <a-descriptions-item label="IP">{{ detail.clientIp || '-' }}</a-descriptions-item>
            <a-descriptions-item label="模块">{{ detail.module }}</a-descriptions-item>
            <a-descriptions-item label="动作">{{ actionLabel(detail.action) }}</a-descriptions-item>
            <a-descriptions-item label="资源">
              {{ resourceTypeLabel(detail.resourceType) }} / {{ detail.resourceId || '-' }}
            </a-descriptions-item>
            <a-descriptions-item label="结果">
              <a-tag :color="detail.result === 'SUCCESS' ? 'success' : 'error'">
                {{ detail.result === 'SUCCESS' ? '成功' : '失败' }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item v-if="detail.failReason" label="失败原因">
              {{ detail.failReason }}
            </a-descriptions-item>
          </a-descriptions>
          <h4 class="block-title">操作详情</h4>
          <BizAuditDetailsPanel :action="detail.action" :details="detail.details" />
        </template>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { TablePaginationConfig } from 'ant-design-vue'
import * as auditApi from '@/modules/audit/api/audit'
import type { BizAuditLog } from '@/modules/audit/api/audit'
import BizAuditDetailsPanel from '@/modules/audit/components/BizAuditDetailsPanel.vue'
import { actionLabel } from '@/modules/audit/utils/formatAudit'

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  session: '会话',
  user: '用户',
  dept: '部门',
  role: '角色',
  instance: '实例',
  connection: '连接',
  workspace: '工作空间',
  policy: '策略',
}

function resourceTypeLabel(type?: string) {
  if (!type) return '-'
  return RESOURCE_TYPE_LABELS[type] || type
}

const loading = ref(false)
const rows = ref<BizAuditLog[]>([])
const query = reactive({
  operatorUsername: '',
  module: '',
  action: '',
  result: undefined as string | undefined,
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
  { title: '模块', dataIndex: 'module', key: 'module', width: 120 },
  { title: '动作', dataIndex: 'action', key: 'action', width: 100 },
  { title: '资源类型', dataIndex: 'resourceType', key: 'resourceType', width: 120 },
  { title: '结果', key: 'result', width: 90 },
  { title: '操作', key: 'ops', width: 80 },
]

const detailOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<BizAuditLog | null>(null)

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
    const resp = await auditApi.fetchBizLogs({
      page: pagination.current,
      size: pagination.pageSize,
      operatorUsername: query.operatorUsername || undefined,
      module: query.module || undefined,
      action: query.action || undefined,
      result: query.result,
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
  query.module = ''
  query.action = ''
  query.result = undefined
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
    const resp = await auditApi.fetchBizLogDetail(eventId)
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
.block-title {
  margin: 16px 0 8px;
}
</style>
