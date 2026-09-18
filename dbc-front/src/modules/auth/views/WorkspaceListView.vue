<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>权限管控</a-breadcrumb-item>
      <a-breadcrumb-item>工作空间授权</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>{{ domain.isPersonal ? '工作空间授权（个人）' : '工作空间授权' }}</h2>
      <a-button v-if="canOperate && showCreateBtn" type="primary" @click="openCreate">
        {{ domain.isPersonal ? '创建个人空间' : '新建工作空间' }}
      </a-button>
    </div>
    <a-alert
      type="info"
      show-icon
      style="margin-bottom: 12px"
      :message="
        domain.isPersonal
          ? '个人域仅展示本人个人空间；被授权成员只能通过 SQL 工作台执行，不能在此改配置。'
          : '仅具备工作空间操作权限的用户可创建公司空间。创建后本人为所有者；日常运营在详情页完成。'
      "
    />
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'myRole'">
          <a-tag :color="roleColor(record.myRole)">{{ roleLabel(record.myRole) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'updatedAt'">
          {{ formatTime(record.updatedAt) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a @click="goDetail(record.id)">进入</a>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="createOpen"
      title="新建工作空间"
      :confirm-loading="saving"
      @ok="submitCreate"
      destroy-on-close
    >
      <a-form layout="vertical">
        <a-form-item :label="domain.isPersonal ? '名称（可空，默认「用户名的个人空间」）' : '名称'" :required="!domain.isPersonal">
          <a-input v-model:value="form.name" maxlength="128" :placeholder="domain.isPersonal ? '可选' : '全局唯一'" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" maxlength="512" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as workspaceApi from '@/modules/auth/api/workspace'
import type { WorkspaceListItem } from '@/modules/auth/api/workspace'
import { ROLE_LABELS } from '@/modules/sqlwork/constants'
import { usePermission } from '@/common/permission/usePermission'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { hasPermission } from '@/common/permission/menu'

const { hasPermission: hasPerm } = usePermission()
const domain = useDomainStore()
const auth = useAuthStore()
const canOperate = computed(() => {
  if (hasPerm('auth.workspace.operate')) return true
  return (
    domain.isPersonal &&
    hasPermission(auth.user?.permissions, 'usercenter.personal.space.view')
  )
})
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const rows = ref<WorkspaceListItem[]>([])
const createOpen = ref(false)
const form = reactive({ name: '', description: '' })

const showCreateBtn = computed(() => {
  if (!domain.isPersonal) return true
  return rows.value.length === 0
})

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '所有者用户ID', dataIndex: 'ownerUserId', key: 'ownerUserId', width: 120 },
  { title: '我的角色', key: 'myRole', width: 140 },
  { title: '成员', dataIndex: 'memberCount', key: 'memberCount', width: 80 },
  { title: '挂载连接', dataIndex: 'assetCount', key: 'assetCount', width: 100 },
  { title: '更新时间', key: 'updatedAt', width: 180 },
  { title: '操作', key: 'action', width: 80 },
]

function roleLabel(code: string) {
  return ROLE_LABELS[code] || code
}

function roleColor(code: string) {
  if (code === 'OWNER') return 'gold'
  if (code === 'ADMIN') return 'success'
  return 'default'
}

function formatTime(v?: string) {
  if (!v) return '-'
  return v.replace('T', ' ').slice(0, 19)
}

async function load() {
  loading.value = true
  try {
    const resp = await workspaceApi.listMyWorkspaces()
    rows.value = resp.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.name = ''
  form.description = ''
  createOpen.value = true
}

async function submitCreate() {
  if (!domain.isPersonal && !form.name.trim()) {
    message.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    const resp = domain.isPersonal
      ? await workspaceApi.ensurePersonalWorkspace({
          name: form.name.trim() || undefined,
          description: form.description.trim() || undefined,
        })
      : await workspaceApi.createWorkspace({
          name: form.name.trim(),
          description: form.description.trim() || undefined,
        })
    message.success('已创建')
    createOpen.value = false
    await load()
    if (resp.data?.id) {
      router.push(`/manage/auth/workspaces/${resp.data.id}`)
    }
  } finally {
    saving.value = false
  }
}

function goDetail(id: number) {
  router.push(`/manage/auth/workspaces/${id}`)
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
h2 {
  margin: 0;
  font-size: 20px;
}
</style>
