<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>用户中心</a-breadcrumb-item>
      <a-breadcrumb-item>角色管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <div>
        <h2 class="title">角色管理</h2>
        <p class="note">权限点定义在「权限管理」只读。功能授权：超管角色只读；超管与系统管理员均可改系统管理员；其余角色按 operate 可改。</p>
      </div>
      <a-button v-if="canOperate" type="primary" @click="openCreate">新增角色</a-button>
    </div>
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'dataScope'">
          {{ dataScopeLabel(record.dataScope) }}
        </template>
        <template v-else-if="column.key === 'builtin'">
          {{ record.builtin ? '是' : '否' }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a @click="openView(record)">查看</a>
            <a v-if="canOperate && !record.builtin" @click="openEdit(record)">编辑</a>
            <a v-if="canViewAuth" @click="openAuth(record)">
              {{ canEditTargetAuth(record) ? '功能授权' : '查看授权' }}
            </a>
            <a-popconfirm
              v-if="canOperate && !record.builtin"
              title="确认删除该角色？"
              @confirm="onDelete(record.id)"
            >
              <a class="danger">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="viewOpen" title="角色详情" :footer="null">
      <a-descriptions bordered :column="1" size="small">
        <a-descriptions-item label="角色名称">{{ current?.name }}</a-descriptions-item>
        <a-descriptions-item label="角色编码">{{ current?.code }}</a-descriptions-item>
        <a-descriptions-item label="说明">{{ current?.description }}</a-descriptions-item>
        <a-descriptions-item label="数据范围">{{ dataScopeLabel(current?.dataScope) }}</a-descriptions-item>
        <a-descriptions-item label="内置">{{ current?.builtin ? '是' : '否' }}</a-descriptions-item>
      </a-descriptions>
    </a-modal>

    <a-modal
      v-model:open="editOpen"
      :title="editingId ? '编辑角色' : '新增角色'"
      @ok="submitEdit"
      :confirm-loading="saving"
    >
      <a-form layout="vertical">
        <a-form-item v-if="!editingId" label="角色编码" required>
          <a-input v-model:value="form.code" placeholder="如 OPS_LEAD" />
        </a-form-item>
        <a-form-item label="角色名称" required>
          <a-input v-model:value="form.name" />
        </a-form-item>
        <a-form-item label="说明">
          <a-textarea v-model:value="form.description" :rows="2" />
        </a-form-item>
        <a-form-item label="数据范围" required>
          <a-select v-model:value="form.dataScope" :options="DATA_SCOPE_OPTIONS" />
        </a-form-item>
        <a-form-item v-if="form.dataScope === 'CUSTOM'" label="勾选部门" required>
          <a-tree-select
            v-model:value="form.deptIds"
            tree-checkable
            allow-clear
            style="width: 100%"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="选择部门"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="authOpen"
      :title="authReadonly ? '查看功能授权' : '功能授权'"
      :ok-button-props="{ style: authReadonly ? { display: 'none' } : undefined }"
      :cancel-text="authReadonly ? '关闭' : '取消'"
      @ok="submitAuth"
      :confirm-loading="saving"
      width="520px"
    >
      <p class="auth-tip">勾选操作权限将自动包含同功能查看权限。</p>
      <a-spin :spinning="authLoading">
        <a-tree
          v-if="authTreeData.length"
          checkable
          default-expand-all
          :disabled="authReadonly"
          :tree-data="authTreeData"
          v-model:checkedKeys="authCheckedKeys"
          @check="onAuthCheck"
        />
        <a-empty v-else description="暂无权限数据" />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { DataNode } from 'ant-design-vue/es/tree'
import * as roleApi from '@/modules/user-center/api/role'
import * as deptApi from '@/modules/user-center/api/dept'
import * as permApi from '@/modules/user-center/api/permission'
import {
  DATA_SCOPE_OPTIONS,
  dataScopeLabel,
  type DeptTreeNode,
  type PermissionView,
  type RoleView,
} from '@/modules/user-center/api/types'
import { usePermission } from '@/common/permission/usePermission'
import { useAuthStore } from '@/modules/user-center/stores/auth'

const auth = useAuthStore()
const { hasPermission } = usePermission()
const canOperate = computed(() => hasPermission('usercenter.role.operate'))
const canViewAuth = computed(() => hasPermission('usercenter.role.view'))
const actorIsSuper = computed(() => !!auth.user?.roles?.some((r) => r.code === 'SUPER_ADMIN'))
const actorIsSys = computed(() => !!auth.user?.roles?.some((r) => r.code === 'SYS_ADMIN'))

/** 是否可编辑目标角色的功能授权（需同时具备 role.operate） */
function canEditTargetAuth(record: RoleView): boolean {
  if (!canOperate.value) return false
  if (record.code === 'SUPER_ADMIN') return false
  if (record.code === 'SYS_ADMIN') return actorIsSuper.value || actorIsSys.value
  return true
}

const loading = ref(false)
const saving = ref(false)
const rows = ref<RoleView[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const allPerms = ref<PermissionView[]>([])
const viewOpen = ref(false)
const editOpen = ref(false)
const authOpen = ref(false)
const authLoading = ref(false)
const authReadonly = ref(false)
const authRoleId = ref<number | null>(null)
const authCheckedKeys = ref<(string | number)[]>([])
const current = ref<RoleView | null>(null)
const editingId = ref<number | null>(null)
const form = reactive({
  code: '',
  name: '',
  description: '',
  dataScope: 'DEPT_AND_CHILDREN',
  deptIds: [] as number[],
})

const columns = [
  { title: '角色名称', dataIndex: 'name', key: 'name' },
  { title: '角色编码', dataIndex: 'code', key: 'code' },
  { title: '数据范围', key: 'dataScope' },
  { title: '说明', dataIndex: 'description', key: 'description' },
  { title: '内置', key: 'builtin' },
  { title: '操作', key: 'action' },
]

const authTreeData = computed<DataNode[]>(() => buildAuthTree(allPerms.value))

function buildAuthTree(perms: PermissionView[]): DataNode[] {
  const modules = new Map<string, Map<string, PermissionView[]>>()
  for (const p of perms) {
    if (!modules.has(p.moduleCode)) modules.set(p.moduleCode, new Map())
    const features = modules.get(p.moduleCode)!
    if (!features.has(p.featureCode)) features.set(p.featureCode, [])
    features.get(p.featureCode)!.push(p)
  }
  const tree: DataNode[] = []
  for (const [moduleCode, features] of modules) {
    const moduleName = perms.find((p) => p.moduleCode === moduleCode)?.moduleName || moduleCode
    const featureNodes: DataNode[] = []
    for (const [featureCode, list] of features) {
      const featureName = list[0]?.featureName || featureCode
      featureNodes.push({
        key: `f:${moduleCode}:${featureCode}`,
        title: featureName,
        children: list.map((p) => ({
          key: p.id,
          title: `${p.name}（${p.code.endsWith('.operate') ? '操作' : '查看'}）`,
          isLeaf: true,
        })),
      })
    }
    tree.push({
      key: `m:${moduleCode}`,
      title: moduleName,
      children: featureNodes,
    })
  }
  return tree
}

function openView(record: RoleView) {
  current.value = record
  viewOpen.value = true
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    code: '',
    name: '',
    description: '',
    dataScope: 'DEPT_AND_CHILDREN',
    deptIds: [],
  })
  editOpen.value = true
}

function openEdit(record: RoleView) {
  editingId.value = record.id
  Object.assign(form, {
    code: record.code,
    name: record.name,
    description: record.description || '',
    dataScope: record.dataScope || 'DEPT_AND_CHILDREN',
    deptIds: record.deptIds || [],
  })
  editOpen.value = true
}

async function openAuth(record: RoleView) {
  authRoleId.value = record.id
  authReadonly.value = !canEditTargetAuth(record)
  authOpen.value = true
  authLoading.value = true
  try {
    if (!allPerms.value.length) {
      // 树数据接口校验 permission.view（无则由后端 403，业务流程需一并授予）
      const all = await permApi.fetchAllPermissions()
      allPerms.value = all.data || []
    }
    const resp = await permApi.fetchRolePermissionIds(record.id)
    authCheckedKeys.value = [...(resp.data || [])]
  } finally {
    authLoading.value = false
  }
}

function onAuthCheck(
  checked: (string | number)[] | { checked: (string | number)[]; halfChecked: (string | number)[] },
) {
  const keys = Array.isArray(checked) ? checked : checked.checked
  const leafIds = keys.filter((k) => typeof k === 'number') as number[]
  const byFeature = new Map<string, PermissionView[]>()
  for (const p of allPerms.value) {
    const fk = `${p.moduleCode}.${p.featureCode}`
    if (!byFeature.has(fk)) byFeature.set(fk, [])
    byFeature.get(fk)!.push(p)
  }
  const next = new Set<number>(leafIds)
  for (const [, list] of byFeature) {
    const view = list.find((p) => p.code.endsWith('.view'))
    const operate = list.find((p) => p.code.endsWith('.operate'))
    if (operate && next.has(operate.id) && view) {
      next.add(view.id)
    }
  }
  authCheckedKeys.value = [...next]
}

async function submitAuth() {
  if (authReadonly.value || !authRoleId.value) {
    authOpen.value = false
    return
  }
  const ids = authCheckedKeys.value.filter((k) => typeof k === 'number') as number[]
  saving.value = true
  try {
    await permApi.updateRolePermissions(authRoleId.value, ids)
    message.success('功能授权已保存')
    authOpen.value = false
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  if (!form.name.trim()) {
    message.warning('请填写角色名称')
    return
  }
  if (!editingId.value && !form.code.trim()) {
    message.warning('请填写角色编码')
    return
  }
  if (form.dataScope === 'CUSTOM' && (!form.deptIds || !form.deptIds.length)) {
    message.warning('请勾选部门')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await roleApi.updateRole(editingId.value, {
        name: form.name.trim(),
        description: form.description || undefined,
        dataScope: form.dataScope,
        deptIds: form.dataScope === 'CUSTOM' ? form.deptIds : undefined,
      })
    } else {
      await roleApi.createRole({
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        description: form.description || undefined,
        dataScope: form.dataScope,
        deptIds: form.dataScope === 'CUSTOM' ? form.deptIds : undefined,
      })
    }
    message.success('已保存')
    editOpen.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  await roleApi.deleteRole(id)
  message.success('已删除')
  await load()
}

async function load() {
  loading.value = true
  try {
    const resp = await roleApi.fetchRoles()
    rows.value = resp.data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    if (hasPermission('usercenter.dept.view')) {
      const deptResp = await deptApi.fetchDeptTree()
      deptTree.value = deptResp.data || []
    }
  } catch {
    deptTree.value = []
  }
  await load()
})
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
  gap: 16px;
}
.title { margin: 0 0 8px; font-size: 20px; }
.note { color: rgba(0,0,0,.45); margin: 0; }
.danger { color: #ff4d4f; }
.auth-tip { color: rgba(0,0,0,.45); margin-bottom: 12px; }
</style>
