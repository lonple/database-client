<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>系统管理</a-breadcrumb-item>
      <a-breadcrumb-item>应用管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>应用管理</h2>
      <a-space>
        <a-button @click="onProbe">签名自测</a-button>
        <a-button @click="onRotateSelf">轮换本服务签名密钥</a-button>
        <a-button type="primary" @click="createOpen = true">登记应用</a-button>
      </a-space>
    </div>
    <a-table row-key="id" :columns="columns" :data-source="rows" :loading="loading" :pagination="false">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 1 ? 'success' : 'default'">
            {{ record.status === 1 ? '启用' : '停用' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'builtin'">
          {{ record.builtin === 1 ? '是' : '否' }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a @click="openKeys(record)">公钥</a>
            <a-popconfirm title="确认重新签发客户端证书？服务需更换本地 p12。" @confirm="onReissue(record.id)">
              <a>重签证书</a>
            </a-popconfirm>
            <a
              v-if="record.builtin !== 1"
              @click="onToggle(record)"
            >{{ record.status === 1 ? '停用' : '启用' }}</a>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="createOpen" title="登记应用" @ok="submitCreate" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="clientId" required>
          <a-input v-model:value="createForm.clientId" placeholder="如 dbc-asset" />
        </a-form-item>
        <a-form-item label="应用名称" required>
          <a-input v-model:value="createForm.appName" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer v-model:open="keysOpen" :title="`公钥 - ${currentApp?.clientId || ''}`" width="720">
      <a-table row-key="id" size="small" :columns="keyColumns" :data-source="keys" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'alive'">
            <a-tag :color="record.alive ? 'success' : 'default'">{{ record.alive ? '存活' : '失活/吊销' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-popconfirm
              v-if="record.status === 'active'"
              title="确认吊销该 kid？"
              @confirm="onRevoke(record.kid)"
            >
              <a class="danger">吊销</a>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as appApi from '@/modules/system/api/app'
import type { AppKeyView, AppView } from '@/modules/system/api/app'

const loading = ref(false)
const saving = ref(false)
const rows = ref<AppView[]>([])
const createOpen = ref(false)
const createForm = reactive({ clientId: '', appName: '' })
const keysOpen = ref(false)
const currentApp = ref<AppView | null>(null)
const keys = ref<AppKeyView[]>([])

const columns = [
  { title: 'clientId', dataIndex: 'clientId' },
  { title: '名称', dataIndex: 'appName' },
  { title: '内置', key: 'builtin' },
  { title: '状态', key: 'status' },
  { title: '已有证书', dataIndex: 'hasClientCert' },
  { title: '操作', key: 'action' },
]

const keyColumns = [
  { title: 'kid', dataIndex: 'kid', ellipsis: true },
  { title: '算法', dataIndex: 'algorithm', width: 80 },
  { title: '实例', dataIndex: 'instanceId', ellipsis: true },
  { title: '状态', dataIndex: 'status', width: 90 },
  { title: '存活', key: 'alive', width: 100 },
  { title: '最近心跳', dataIndex: 'lastSeenAt', width: 180 },
  { title: '操作', key: 'action', width: 80 },
]

async function load() {
  loading.value = true
  try {
    const resp = await appApi.listApps()
    rows.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  if (!createForm.clientId.trim() || !createForm.appName.trim()) {
    message.warning('请填写完整')
    return
  }
  saving.value = true
  try {
    await appApi.createApp({
      clientId: createForm.clientId.trim(),
      appName: createForm.appName.trim(),
    })
    message.success('已登记，客户端证书已写入 secrets/mtls/clients/')
    createOpen.value = false
    createForm.clientId = ''
    createForm.appName = ''
    await load()
  } catch (e: any) {
    message.error(e?.message || '创建失败')
  } finally {
    saving.value = false
  }
}

async function onReissue(id: number) {
  try {
    await appApi.reissueAppCert(id)
    message.success('已重新签发客户端证书')
    await load()
  } catch (e: any) {
    message.error(e?.message || '重签失败')
  }
}

async function onToggle(record: AppView) {
  try {
    await appApi.updateAppStatus(record.id, record.status === 1 ? 0 : 1)
    await load()
  } catch (e: any) {
    message.error(e?.message || '更新失败')
  }
}

async function openKeys(record: AppView) {
  currentApp.value = record
  keysOpen.value = true
  try {
    const resp = await appApi.listAppKeys(record.id)
    keys.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载公钥失败')
  }
}

async function onRevoke(kid: string) {
  if (!currentApp.value) return
  try {
    await appApi.revokeAppKey(currentApp.value.id, kid)
    message.success('已吊销')
    const resp = await appApi.listAppKeys(currentApp.value.id)
    keys.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '吊销失败')
  }
}

async function onRotateSelf() {
  try {
    const resp = await appApi.rotateSelfSigningKey()
    message.success(`已轮换，新 kid=${resp.data?.kid || ''}`)
    await load()
  } catch (e: any) {
    message.error(e?.message || '轮换失败')
  }
}

async function onProbe() {
  try {
    const resp = await appApi.probeInnerPing()
    message.success(`自测成功 status=${resp.data?.status} kid=${resp.data?.kid}`)
  } catch (e: any) {
    message.error(e?.message || '自测失败')
  }
}

onMounted(load)
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
</style>
