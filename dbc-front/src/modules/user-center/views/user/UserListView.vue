<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>用户中心</a-breadcrumb-item>
      <a-breadcrumb-item>用户管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>用户管理</h2>
      <a-button v-if="canOperate" type="primary" @click="openCreate">新增用户</a-button>
    </div>
    <a-space style="margin-bottom: 16px">
      <a-input v-model:value="query.username" placeholder="账号" allow-clear style="width: 200px" />
      <a-button @click="load">查询</a-button>
      <a-button @click="resetQuery">重置</a-button>
    </a-space>
    <a-table
      row-key="id"
      :columns="columns"
      :data-source="rows"
      :loading="loading"
      :pagination="pagination"
      @change="onTableChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'default'">
            {{ record.status === 1 ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'roles'">
          {{ (record.roles || []).map((r: RoleBrief) => r.name).join('、') || '-' }}
        </template>
        <template v-else-if="column.key === 'dept'">
          {{ record.deptName || '-' }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a v-if="canOperate" @click="openEdit(record)">编辑</a>
            <a
              v-if="canOperate && !(record.builtin || record.id === auth.user?.id)"
              @click="toggleStatus(record)"
            >{{ record.status === 1 ? '禁用' : '启用' }}</a>
            <a v-if="canOperate" @click="openReset(record)">重置密码</a>
            <a-popconfirm
              v-if="canOperate && !(record.builtin || record.id === auth.user?.id)"
              title="确认删除该用户？"
              @confirm="onDelete(record.id)"
            >
              <a class="danger">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="createOpen" title="新增用户" @ok="submitCreate" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="账号" required>
          <a-input v-model:value="createForm.username" />
        </a-form-item>
        <a-form-item label="密码" required>
          <a-input-password v-model:value="createForm.password" />
        </a-form-item>
        <a-form-item label="角色" required>
          <a-select
            v-model:value="createForm.roleIds"
            mode="multiple"
            :options="roleOptions"
            placeholder="至少选择一个角色"
          />
        </a-form-item>
        <a-form-item label="部门">
          <a-tree-select
            v-model:value="createForm.deptId"
            allow-clear
            style="width: 100%"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="可选"
          />
        </a-form-item>
        <a-form-item label="手机号">
          <a-input v-model:value="createForm.mobile" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="createForm.description" :rows="3" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="createForm.status" :options="statusOptions" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="editOpen" title="编辑用户" @ok="submitEdit" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="账号">
          <a-input :value="editForm.username" disabled />
        </a-form-item>
        <a-form-item label="角色" required>
          <a-select
            v-model:value="editForm.roleIds"
            mode="multiple"
            :options="roleOptions"
            placeholder="至少选择一个角色"
          />
        </a-form-item>
        <a-form-item label="部门">
          <a-tree-select
            v-model:value="editForm.deptId"
            allow-clear
            style="width: 100%"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="可选"
          />
        </a-form-item>
        <a-form-item label="手机号">
          <a-input v-model:value="editForm.mobile" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editForm.description" :rows="3" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select
            v-model:value="editForm.status"
            :options="statusOptions"
            :disabled="!!editForm.builtin"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="resetOpen" title="重置密码" @ok="submitReset" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="新密码" required>
          <a-input-password v-model:value="resetForm.password" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { TablePaginationConfig } from 'ant-design-vue'
import * as userApi from '@/modules/user-center/api/user'
import * as deptApi from '@/modules/user-center/api/dept'
import type { DeptTreeNode, RoleBrief, UserView } from '@/modules/user-center/api/types'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { usePermission } from '@/common/permission/usePermission'

const auth = useAuthStore()
const { hasPermission } = usePermission()
const canOperate = computed(() => hasPermission('usercenter.user.operate'))
const loading = ref(false)
const saving = ref(false)
const rows = ref<UserView[]>([])
const roles = ref<RoleBrief[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const query = reactive({ username: '', page: 1, size: 10, total: 0 })

const createOpen = ref(false)
const editOpen = ref(false)
const resetOpen = ref(false)
const createForm = reactive({
  username: '',
  password: '',
  roleIds: [] as number[],
  deptId: undefined as number | undefined,
  mobile: '',
  description: '',
  status: 1,
})
const editForm = reactive({
  id: 0,
  username: '',
  roleIds: [] as number[],
  deptId: undefined as number | undefined,
  mobile: '',
  description: '',
  status: 1,
  builtin: false,
})
const resetForm = reactive({ id: 0, password: '' })

const columns = [
  { title: '账号', dataIndex: 'username', key: 'username' },
  { title: '角色', key: 'roles' },
  { title: '部门', key: 'dept' },
  { title: '手机号', dataIndex: 'mobile', key: 'mobile' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '状态', key: 'status' },
  { title: '操作', key: 'action' },
]

const statusOptions = [
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

const roleOptions = computed(() => roles.value.map((r) => ({ label: r.name, value: r.id })))

const pagination = computed(() => ({
  current: query.page,
  pageSize: query.size,
  total: query.total,
  showSizeChanger: true,
  showTotal: (t: number) => `共 ${t} 条`,
}))

async function loadRoles() {
  try {
    const resp = await userApi.fetchRoles()
    roles.value = resp.data
  } catch {
    roles.value = []
  }
}

async function loadDepts() {
  try {
    const resp = await deptApi.fetchDeptTree()
    deptTree.value = resp.data || []
  } catch {
    deptTree.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const resp = await userApi.fetchUsers({
      page: query.page,
      size: query.size,
      username: query.username || undefined,
    })
    rows.value = resp.data.records
    query.total = resp.data.total
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.username = ''
  query.page = 1
  load()
}

function onTableChange(p: TablePaginationConfig) {
  query.page = p.current || 1
  query.size = p.pageSize || 10
  load()
}

function openCreate() {
  Object.assign(createForm, {
    username: '',
    password: '',
    roleIds: roles.value[1] ? [roles.value[1].id] : [],
    deptId: undefined,
    mobile: '',
    description: '',
    status: 1,
  })
  createOpen.value = true
}

async function submitCreate() {
  if (!createForm.username || !createForm.password || !createForm.roleIds.length) {
    message.warning('请填写必填项（含至少一个角色）')
    return
  }
  saving.value = true
  try {
    await userApi.createUser({
      username: createForm.username,
      password: createForm.password,
      roleIds: createForm.roleIds,
      deptId: createForm.deptId ?? null,
      mobile: createForm.mobile || undefined,
      description: createForm.description || undefined,
      status: createForm.status,
    })
    message.success('创建成功')
    createOpen.value = false
    query.page = 1
    await load()
  } finally {
    saving.value = false
  }
}

function openEdit(record: UserView) {
  Object.assign(editForm, {
    id: record.id,
    username: record.username,
    roleIds: (record.roles || []).map((r) => r.id),
    deptId: record.deptId ?? undefined,
    mobile: record.mobile || '',
    description: record.description || '',
    status: record.status,
    builtin: record.builtin,
  })
  editOpen.value = true
}

async function submitEdit() {
  if (!editForm.roleIds.length) {
    message.warning('请至少选择一个角色')
    return
  }
  saving.value = true
  try {
    await userApi.updateUser(editForm.id, {
      roleIds: editForm.roleIds,
      deptId: editForm.deptId ?? null,
      mobile: editForm.mobile || undefined,
      description: editForm.description || undefined,
      status: editForm.status,
    })
    message.success('保存成功')
    editOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function toggleStatus(record: UserView) {
  await userApi.updateUser(record.id, {
    roleIds: (record.roles || []).map((r) => r.id),
    deptId: record.deptId ?? null,
    mobile: record.mobile || undefined,
    description: record.description || undefined,
    status: record.status === 1 ? 0 : 1,
  })
  message.success('已更新状态')
  await load()
}

function openReset(record: UserView) {
  resetForm.id = record.id
  resetForm.password = ''
  resetOpen.value = true
}

async function submitReset() {
  if (!resetForm.password) {
    message.warning('请输入新密码')
    return
  }
  saving.value = true
  try {
    await userApi.resetPassword(resetForm.id, resetForm.password)
    message.success('密码已重置')
    resetOpen.value = false
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  await userApi.deleteUser(id)
  message.success('已删除')
  await load()
}

onMounted(async () => {
  await Promise.all([loadRoles(), loadDepts()])
  await load()
})
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.title-row h2 { margin: 0; font-size: 20px; }
.danger { color: #ff4d4f; }
</style>
