<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>资产管理</a-breadcrumb-item>
      <a-breadcrumb-item>连接管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>连接管理</h2>
      <a-button v-if="canOperate" type="primary" @click="openCreate">新增连接</a-button>
    </div>
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'dbType'">
          {{ dbTypeLabel(record.dbType) }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'default'">
            {{ record.status === 1 ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a v-if="canOperate" @click="openEdit(record)">编辑</a>
            <a-popconfirm v-if="canOperate" title="确认删除该连接？" @confirm="onDelete(record.id)">
              <a class="danger">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formOpen"
      :title="editingId ? '编辑连接' : '新增连接'"
      :confirm-loading="saving"
      :ok-button-props="{ disabled: testing }"
      @ok="submitForm"
      destroy-on-close
    >
      <a-form layout="vertical">
        <a-form-item label="连接名" required>
          <a-input v-model:value="form.name" maxlength="128" />
        </a-form-item>
        <a-form-item v-if="!domain.isPersonal" label="归属部门" required>
          <a-tree-select
            v-model:value="form.deptId"
            style="width: 100%"
            :tree-data="deptTree"
            :field-names="{ label: 'name', value: 'id', children: 'children' }"
            tree-default-expand-all
            placeholder="选择部门"
          />
        </a-form-item>
        <a-form-item label="数据库类型" required>
          <a-select
            v-model:value="form.dbType"
            :options="DB_TYPE_OPTIONS"
            :disabled="!!editingId"
            @change="onDbTypeChange"
          />
        </a-form-item>
        <a-form-item label="实例" required>
          <a-select
            v-model:value="form.instanceId"
            :options="instanceOptions"
            show-search
            option-filter-prop="label"
            placeholder="选择实例"
          />
        </a-form-item>
        <a-form-item label="用户名" required>
          <a-input v-model:value="form.username" />
        </a-form-item>
        <a-form-item :label="editingId ? '密码（留空不修改）' : '密码'" :required="!editingId">
          <a-input-password v-model:value="form.password" />
        </a-form-item>
        <a-form-item label="初始数据库">
          <a-input v-model:value="form.initialDatabase" />
        </a-form-item>
        <a-form-item label="状态">
          <a-switch
            :checked="form.status === 1"
            checked-children="启用"
            un-checked-children="停用"
            @change="(v: boolean) => (form.status = v ? 1 : 0)"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <div class="modal-footer">
          <a-button :loading="testing" @click="onTestConnection">连接测试</a-button>
          <a-space>
            <a-button @click="formOpen = false">取消</a-button>
            <a-button type="primary" :loading="saving" :disabled="testing" @click="submitForm">确定</a-button>
          </a-space>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as assetApi from '@/modules/manage/api/asset'
import type { ConnectionView, DeptTreeNode, InstanceView } from '@/modules/manage/api/asset'
import { DB_TYPE_OPTIONS } from '@/modules/manage/constants'
import { usePermission } from '@/common/permission/usePermission'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { hasPermission } from '@/common/permission/menu'

const { hasPermission: hasPerm } = usePermission()
const domain = useDomainStore()
const auth = useAuthStore()
const canOperate = computed(() => {
  if (hasPerm('manage.connection.operate')) return true
  return (
    domain.isPersonal &&
    hasPermission(auth.user?.permissions, 'usercenter.personal.space.view')
  )
})

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const rows = ref<ConnectionView[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const selectable = ref<InstanceView[]>([])
const formOpen = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  deptId: undefined as number | undefined,
  dbType: 'POSTGRESQL',
  instanceId: undefined as number | undefined,
  username: '',
  password: '',
  initialDatabase: '',
  status: 1,
})

const columns = computed(() => {
  const cols: any[] = [
    { title: '连接名', dataIndex: 'name' },
    { title: '实例', dataIndex: 'instanceName' },
    { title: '类型', key: 'dbType', width: 110 },
    { title: '用户名', dataIndex: 'username' },
    { title: '初始库', dataIndex: 'initialDatabase' },
  ]
  if (!domain.isPersonal) {
    cols.push({ title: '部门ID', dataIndex: 'deptId', width: 90 })
  }
  cols.push(
    { title: '状态', key: 'status', width: 90 },
    { title: '操作', key: 'action', width: 140 },
  )
  return cols
})

const instanceOptions = computed(() =>
  selectable.value.map((i) => ({
    value: i.id,
    label: `${i.name} (${i.host}:${i.port})`,
  })),
)

function dbTypeLabel(code: string) {
  return DB_TYPE_OPTIONS.find((o) => o.value === code)?.label || code
}

async function load() {
  loading.value = true
  try {
    const resp = await assetApi.listConnections()
    rows.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDepts() {
  try {
    const resp = await assetApi.listDeptTree()
    deptTree.value = resp.data || []
  } catch {
    deptTree.value = []
  }
}

async function loadSelectable(dbType?: string) {
  try {
    const resp = await assetApi.listSelectableInstances(dbType)
    selectable.value = resp.data || []
  } catch {
    selectable.value = []
  }
}

function onDbTypeChange() {
  form.instanceId = undefined
  loadSelectable(form.dbType)
}

function openCreate() {
  editingId.value = null
  form.name = ''
  form.deptId = undefined
  form.dbType = 'POSTGRESQL'
  form.instanceId = undefined
  form.username = ''
  form.password = ''
  form.initialDatabase = ''
  form.status = 1
  formOpen.value = true
  loadSelectable(form.dbType)
}

function openEdit(row: ConnectionView) {
  editingId.value = row.id
  form.name = row.name
  form.deptId = row.deptId ?? undefined
  form.dbType = row.dbType
  form.instanceId = row.instanceId
  form.username = row.username
  form.password = ''
  form.initialDatabase = row.initialDatabase || ''
  form.status = row.status
  formOpen.value = true
  loadSelectable(row.dbType)
}

async function onTestConnection() {
  if (!form.instanceId || !form.username.trim()) {
    message.warning('请先选择实例并填写用户名')
    return
  }
  if (!editingId.value && !form.password) {
    message.warning('请填写密码')
    return
  }
  testing.value = true
  try {
    const resp = await assetApi.pingConnection({
      connectionId: editingId.value ?? undefined,
      instanceId: form.instanceId,
      username: form.username.trim(),
      password: form.password || undefined,
      initialDatabase: form.initialDatabase.trim() || undefined,
    })
    const data = resp.data
    if (data?.success) {
      message.success(data.message ? `${data.message}（${data.latencyMs} ms）` : `连接成功（${data.latencyMs} ms）`)
    } else {
      message.error(data?.message || '连接失败')
    }
  } catch (e: any) {
    message.error(e?.message || '连接测试失败')
  } finally {
    testing.value = false
  }
}

async function submitForm() {
  if (!form.name.trim() || !form.instanceId || !form.username.trim()) {
    message.warning('请填写完整')
    return
  }
  if (!domain.isPersonal && !form.deptId) {
    message.warning('请选择归属部门')
    return
  }
  if (!editingId.value && !form.password) {
    message.warning('请填写密码')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await assetApi.updateConnection(editingId.value, {
        name: form.name.trim(),
        deptId: domain.isPersonal ? undefined : form.deptId,
        instanceId: form.instanceId,
        username: form.username.trim(),
        password: form.password || undefined,
        initialDatabase: form.initialDatabase.trim() || undefined,
        status: form.status,
      })
      message.success('已更新')
    } else {
      await assetApi.createConnection({
        name: form.name.trim(),
        deptId: domain.isPersonal ? undefined : form.deptId,
        instanceId: form.instanceId,
        username: form.username.trim(),
        password: form.password,
        initialDatabase: form.initialDatabase.trim() || undefined,
        status: form.status,
      })
      message.success('已创建')
    }
    formOpen.value = false
    await load()
  } catch (e: any) {
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  try {
    await assetApi.deleteConnection(id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error(e?.message || '删除失败')
  }
}

onMounted(async () => {
  await load()
  if (!domain.isPersonal) {
    await loadDepts()
  }
})
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.danger {
  color: #cf1322;
}
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>
