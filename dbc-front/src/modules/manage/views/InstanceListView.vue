<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>资产管理</a-breadcrumb-item>
      <a-breadcrumb-item>实例管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>实例管理</h2>
      <a-button v-if="canOperate" type="primary" @click="openCreate">新增实例</a-button>
    </div>
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'dbType'">
          {{ dbTypeLabel(record.dbType) }}
        </template>
        <template v-else-if="column.key === 'endpoint'">
          {{ record.host }}:{{ record.port }}
        </template>
        <template v-else-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'default'">
            {{ record.status === 1 ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'driver'">
          {{ record.driverFileName || '未上传' }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a v-if="canOperate" @click="openEdit(record)">编辑</a>
            <a v-if="canOperate" @click="openDriver(record)">驱动</a>
            <a-popconfirm v-if="canOperate" title="确认删除该实例？" @confirm="onDelete(record.id)">
              <a class="danger">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal
      v-model:open="formOpen"
      :title="editingId ? '编辑实例' : '新增实例'"
      :confirm-loading="saving"
      @ok="submitForm"
      destroy-on-close
    >
      <a-form layout="vertical">
        <a-form-item label="实例名" required>
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
          <a-select v-model:value="form.dbType" :options="DB_TYPE_OPTIONS" />
        </a-form-item>
        <a-form-item label="主机" required>
          <a-input v-model:value="form.host" />
        </a-form-item>
        <a-form-item label="端口" required>
          <a-input-number v-model:value="form.port" :min="1" :max="65535" style="width: 100%" />
        </a-form-item>
        <a-form-item label="驱动类名">
          <a-input v-model:value="form.driverClassName" placeholder="可空，按库类型默认" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" />
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
    </a-modal>

    <a-modal v-model:open="driverOpen" title="上传驱动 JAR" :confirm-loading="saving" @ok="submitDriver">
      <a-upload :before-upload="beforeDriver" :max-count="1" accept=".jar" :file-list="driverFileList">
        <a-button>选择 .jar</a-button>
      </a-upload>
      <p class="hint">原始文件名可重复；服务端以唯一路径落盘。</p>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import type { UploadProps } from 'ant-design-vue'
import * as assetApi from '@/modules/manage/api/asset'
import type { DeptTreeNode, InstanceView } from '@/modules/manage/api/asset'
import { DB_TYPE_OPTIONS } from '@/modules/manage/constants'
import { usePermission } from '@/common/permission/usePermission'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import { hasPermission } from '@/common/permission/menu'
import { useAuthStore } from '@/modules/user-center/stores/auth'

const { hasPermission: hasPerm } = usePermission()
const domain = useDomainStore()
const auth = useAuthStore()
const canOperate = computed(() => {
  if (hasPerm('manage.instance.operate')) return true
  return (
    domain.isPersonal &&
    hasPermission(auth.user?.permissions, 'usercenter.personal.space.view')
  )
})

const loading = ref(false)
const saving = ref(false)
const rows = ref<InstanceView[]>([])
const deptTree = ref<DeptTreeNode[]>([])
const formOpen = ref(false)
const driverOpen = ref(false)
const editingId = ref<number | null>(null)
const currentId = ref<number | null>(null)
const driverFile = ref<File | null>(null)
const driverFileList = ref<UploadProps['fileList']>([])

const form = reactive({
  name: '',
  deptId: undefined as number | undefined,
  dbType: 'POSTGRESQL',
  host: '',
  port: 5432,
  driverClassName: '',
  description: '',
  status: 1,
})

const columns = computed(() => {
  const cols: any[] = [
    { title: '实例名', dataIndex: 'name' },
    { title: '类型', key: 'dbType', width: 110 },
    { title: '地址', key: 'endpoint' },
  ]
  if (!domain.isPersonal) {
    cols.push({ title: '部门ID', dataIndex: 'deptId', width: 90 })
  }
  cols.push(
    { title: '驱动', key: 'driver' },
    { title: '状态', key: 'status', width: 90 },
    { title: '操作', key: 'action', width: 180 },
  )
  return cols
})

function dbTypeLabel(code: string) {
  return DB_TYPE_OPTIONS.find((o) => o.value === code)?.label || code
}

async function load() {
  loading.value = true
  try {
    const resp = await assetApi.listInstances()
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

function resetForm() {
  form.name = ''
  form.deptId = undefined
  form.dbType = 'POSTGRESQL'
  form.host = ''
  form.port = 5432
  form.driverClassName = ''
  form.description = ''
  form.status = 1
}

function openCreate() {
  editingId.value = null
  resetForm()
  formOpen.value = true
}

function openEdit(row: InstanceView) {
  editingId.value = row.id
  form.name = row.name
  form.deptId = row.deptId ?? undefined
  form.dbType = row.dbType
  form.host = row.host
  form.port = row.port
  form.driverClassName = row.driverClassName || ''
  form.description = row.description || ''
  form.status = row.status
  formOpen.value = true
}

async function submitForm() {
  if (!form.name.trim() || !form.host.trim() || !form.port) {
    message.warning('请填写完整')
    return
  }
  if (!domain.isPersonal && !form.deptId) {
    message.warning('请选择归属部门')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      deptId: domain.isPersonal ? undefined : form.deptId,
      dbType: form.dbType,
      host: form.host.trim(),
      port: form.port,
      driverClassName: form.driverClassName.trim() || undefined,
      description: form.description.trim() || undefined,
      status: form.status,
    }
    if (editingId.value) {
      await assetApi.updateInstance(editingId.value, payload)
      message.success('已更新')
    } else {
      await assetApi.createInstance(payload)
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

function openDriver(row: InstanceView) {
  currentId.value = row.id
  driverFile.value = null
  driverFileList.value = []
  driverOpen.value = true
}

const beforeDriver: UploadProps['beforeUpload'] = (file) => {
  driverFile.value = file as File
  driverFileList.value = [{ uid: '-1', name: file.name, status: 'done' }]
  return false
}

async function submitDriver() {
  if (!currentId.value || !driverFile.value) {
    message.warning('请选择 jar 文件')
    return
  }
  saving.value = true
  try {
    await assetApi.uploadInstanceDriver(currentId.value, driverFile.value)
    message.success('驱动已上传')
    driverOpen.value = false
    await load()
  } catch (e: any) {
    message.error(e?.message || '上传失败')
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  try {
    await assetApi.deleteInstance(id)
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
.hint {
  margin-top: 12px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}
</style>
