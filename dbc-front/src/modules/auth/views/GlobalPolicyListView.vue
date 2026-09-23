<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>权限管控</a-breadcrumb-item>
      <a-breadcrumb-item>全局管控</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>全局管控</h2>
      <a-button v-if="canOperate" type="primary" @click="openCreate">新增策略</a-button>
    </div>
    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 12px"
      message="策略叠加在工作空间授权之上。阻断优先于二次鉴权，再次于告警；告警仍可执行并在执行日志标红。"
    />
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'ops'">
          {{ formatSqlOps(record.ops).join(', ') }}
        </template>
        <template v-else-if="column.key === 'strategy'">
          <a-tag :color="strategyColor(record.strategy)">{{ strategyLabel(record.strategy) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'workspace'">
          {{ record.workspaceScope === 'ALL' ? '全部空间' : `指定 ${record.workspaceIds?.length || 0} 个` }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'default'">
            {{ record.status === 1 ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a v-if="canOperate" @click="openEdit(record)">编辑</a>
          <a-divider v-if="canOperate" type="vertical" />
          <a-popconfirm v-if="canOperate" title="确认删除该策略？" @confirm="onDelete(record.id)">
            <a class="danger">删除</a>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="modalOpen"
      :title="editingId ? '编辑策略' : '新增策略'"
      :confirm-loading="saving"
      width="640px"
      @ok="submit"
      destroy-on-close
    >
      <a-form layout="vertical">
        <a-form-item label="管控名称" required>
          <a-input v-model:value="form.name" maxlength="128" />
        </a-form-item>
        <a-form-item label="管控指令" required>
          <SqlOpsPicker v-model="form.ops" />
        </a-form-item>
        <a-form-item label="管控策略" required>
          <a-radio-group v-model:value="form.strategy">
            <a-radio value="BLOCK">阻断</a-radio>
            <a-radio value="ALERT">告警</a-radio>
            <a-radio value="REAUTH">二次鉴权</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="管控空间" required>
          <a-radio-group v-model:value="form.workspaceScope">
            <a-radio value="ALL">全部空间</a-radio>
            <a-radio value="SPECIFIC">指定空间</a-radio>
          </a-radio-group>
          <a-select
            v-if="form.workspaceScope === 'SPECIFIC'"
            v-model:value="form.workspaceIds"
            mode="multiple"
            style="width: 100%; margin-top: 8px"
            placeholder="选择工作空间"
            :options="workspaceOptions"
          />
        </a-form-item>
        <a-form-item label="排序号">
          <a-input-number v-model:value="form.sortNo" :min="0" style="width: 160px" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch
            :checked="form.status === 1"
            checked-children="启用"
            un-checked-children="停用"
            @change="(c: boolean) => (form.status = c ? 1 : 0)"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as api from '@/modules/auth/api/globalPolicy'
import type { GlobalPolicy } from '@/modules/auth/api/globalPolicy'
import * as workspaceApi from '@/modules/auth/api/workspace'
import SqlOpsPicker from '@/modules/auth/components/SqlOpsPicker.vue'
import { formatSqlOps, normalizeSqlOps } from '@/modules/auth/utils/sqlOps'
import { usePermission } from '@/common/permission/usePermission'

const { hasPermission } = usePermission()
const canOperate = computed(() => hasPermission('auth.global.policy.operate'))

const loading = ref(false)
const saving = ref(false)
const rows = ref<GlobalPolicy[]>([])
const modalOpen = ref(false)
const editingId = ref<number | null>(null)
const workspaceOptions = ref<{ label: string; value: number }[]>([])

const form = reactive({
  name: '',
  ops: [] as string[],
  strategy: 'BLOCK',
  workspaceScope: 'ALL',
  workspaceIds: [] as number[],
  sortNo: 0,
  status: 1,
})

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '管控指令', key: 'ops' },
  { title: '策略', key: 'strategy', width: 120 },
  { title: '管控空间', key: 'workspace', width: 140 },
  { title: '排序', dataIndex: 'sortNo', key: 'sortNo', width: 80 },
  { title: '状态', key: 'status', width: 90 },
  { title: '操作', key: 'action', width: 120 },
]

function strategyLabel(s: string) {
  if (s === 'BLOCK') return '阻断'
  if (s === 'ALERT') return '告警'
  if (s === 'REAUTH') return '二次鉴权'
  return s
}

function strategyColor(s: string) {
  if (s === 'BLOCK') return 'error'
  if (s === 'ALERT') return 'warning'
  if (s === 'REAUTH') return 'processing'
  return 'default'
}

function resetForm() {
  form.name = ''
  form.ops = []
  form.strategy = 'BLOCK'
  form.workspaceScope = 'ALL'
  form.workspaceIds = []
  form.sortNo = 0
  form.status = 1
}

async function load() {
  loading.value = true
  try {
    const resp = await api.listGlobalPolicies()
    rows.value = (resp.data || []) as GlobalPolicy[]
  } finally {
    loading.value = false
  }
}

async function loadWorkspaces() {
  try {
    const resp = await workspaceApi.listMyWorkspaces()
    workspaceOptions.value = (resp.data || []).map((w: { id: number; name: string }) => ({
      label: w.name,
      value: w.id,
    }))
  } catch {
    workspaceOptions.value = []
  }
}

function openCreate() {
  editingId.value = null
  resetForm()
  modalOpen.value = true
}

function openEdit(row: GlobalPolicy) {
  editingId.value = row.id
  form.name = row.name
  form.ops = [...(row.ops || [])]
  form.strategy = row.strategy
  form.workspaceScope = row.workspaceScope
  form.workspaceIds = [...(row.workspaceIds || [])]
  form.sortNo = row.sortNo ?? 0
  form.status = row.status ?? 1
  modalOpen.value = true
}

async function submit() {
  if (!form.name.trim()) {
    message.warning('请填写管控名称')
    return
  }
  if (!form.ops.length) {
    message.warning('请勾选管控指令，或选择「所有权限（任意 SQL）」')
    return
  }
  if (form.workspaceScope === 'SPECIFIC' && !form.workspaceIds.length) {
    message.warning('请选择至少一个工作空间')
    return
  }
  saving.value = true
  try {
    const body = {
      name: form.name.trim(),
      ops: normalizeSqlOps(form.ops),
      strategy: form.strategy,
      workspaceScope: form.workspaceScope,
      workspaceIds: form.workspaceScope === 'SPECIFIC' ? [...form.workspaceIds] : [],
      sortNo: form.sortNo ?? 0,
      status: form.status,
    }
    if (editingId.value) {
      await api.updateGlobalPolicy(editingId.value, body)
      message.success('已更新')
    } else {
      await api.createGlobalPolicy(body)
      message.success('已创建')
    }
    modalOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  await api.deleteGlobalPolicy(id)
  message.success('已删除')
  await load()
}

onMounted(async () => {
  await Promise.all([load(), loadWorkspaces()])
})
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
h2 {
  margin: 0;
  font-size: 20px;
}
.danger {
  color: #ff4d4f;
}
</style>
