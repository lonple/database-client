<template>
  <div class="pick-layout">
    <aside class="pick-side">
      <div class="side-hd">工作空间</div>
      <div class="side-body">
        <a-spin :spinning="listLoading">
          <a-empty
            v-if="!listLoading && !workspaces.length"
            description="暂无可用空间"
            :image="simpleImage"
          />
          <ul v-else class="ws-list">
            <li
              v-for="w in workspaces"
              :key="w.id"
              class="ws-item"
              :class="{ active: selectedId === w.id }"
              @click="selectWorkspace(w.id)"
            >
              <div class="ws-name" :title="w.name">{{ w.name }}</div>
              <div class="ws-meta">
                <a-tag v-if="w.spaceType === 'PERSONAL'" color="blue">个人</a-tag>
                <a-tag :color="roleColor(w.role)">{{ roleLabel(w.role) }}</a-tag>
              </div>
            </li>
          </ul>
        </a-spin>
      </div>
    </aside>

    <main class="pick-main">
      <template v-if="!selectedId">
        <div class="placeholder">
          <a-empty description="请从左侧选择工作空间" :image="simpleImage" />
          <p class="hint">进入后可按当前空间的连接授权执行 SQL；无空间时请联系管理员创建并添加成员授权。</p>
        </div>
      </template>
      <template v-else>
        <a-spin :spinning="authzLoading">
          <div v-if="authz" class="authz-panel">
            <div class="panel-hd">
              <div class="panel-titles">
                <h2>{{ authz.workspaceName }}</h2>
                <div class="panel-sub">
                  <a-tag v-if="authz.spaceType === 'PERSONAL'" color="blue">个人空间</a-tag>
                  <a-tag :color="roleColor(authz.role)">{{ roleLabel(authz.role) }}</a-tag>
                  <a-tag v-if="authz.spaceManager" color="gold">空间全部资产</a-tag>
                  <a-tag v-else-if="authz.grantAll" color="cyan">授权：全部资产</a-tag>
                  <a-tag v-else color="default">授权：指定资产</a-tag>
                </div>
                <p v-if="authz.description" class="desc">{{ authz.description }}</p>
              </div>
              <a-button type="primary" size="large" @click="enter">进入工作台</a-button>
            </div>

            <a-alert
              v-if="authz.spaceManager"
              type="info"
              show-icon
              style="margin-bottom: 12px"
              message="你是空间所有者或管理员，可使用本空间挂载的全部资产与其操作权限。"
            />
            <a-alert
              v-else-if="authz.grantAll"
              type="info"
              show-icon
              style="margin-bottom: 12px"
              message="成员授权为「全部空间资产」，可见范围与空间资产清单一致。"
            />

            <div class="section-title">可访问资产与权限</div>
            <a-table
              row-key="rowKey"
              size="middle"
              :columns="columns"
              :data-source="grantRows"
              :pagination="grantRows.length > 10 ? { pageSize: 10 } : false"
              :locale="{ emptyText: '当前空间下暂无可用资产' }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'connection'">
                  <div class="conn-cell">
                    <strong>{{ record.connectionName || '—' }}</strong>
                    <span v-if="record.dbType" class="muted">{{ record.dbType }}</span>
                  </div>
                </template>
                <template v-else-if="column.key === 'scope'">
                  {{ scopeLabel(record.scope) }}
                </template>
                <template v-else-if="column.key === 'objects'">
                  <span v-if="isWideScope(record.scope)" class="muted">整库 / 整模式范围</span>
                  <template v-else-if="record.tables?.length">
                    <a-tag
                      v-for="(t, i) in record.tables.slice(0, 6)"
                      :key="i"
                      class="obj-tag"
                    >
                      {{ formatTable(t) }}
                    </a-tag>
                    <span v-if="record.tables.length > 6" class="muted">
                      +{{ record.tables.length - 6 }}
                    </span>
                  </template>
                  <span v-else class="muted">—</span>
                </template>
                <template v-else-if="column.key === 'ops'">
                  <template v-if="record.ops?.length">
                    <a-tag v-for="op in record.ops" :key="op" color="green">{{ op }}</a-tag>
                  </template>
                  <span v-else class="muted">—</span>
                </template>
              </template>
            </a-table>
          </div>
          <a-empty v-else-if="!authzLoading" description="加载授权失败" :image="simpleImage" />
        </a-spin>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import * as sqlworkApi from '@/modules/sqlwork/api/sqlwork'
import type { MyWorkspaceAuthz, WorkspaceSummary } from '@/modules/sqlwork/api/sqlwork'
import { ROLE_LABELS } from '@/modules/sqlwork/constants'

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const router = useRouter()

const listLoading = ref(false)
const authzLoading = ref(false)
const workspaces = ref<WorkspaceSummary[]>([])
const selectedId = ref<number | undefined>()
const authz = ref<MyWorkspaceAuthz | null>(null)

const columns = [
  { title: '连接', key: 'connection', dataIndex: 'connectionName', width: 200 },
  { title: '范围', key: 'scope', dataIndex: 'scope', width: 110 },
  { title: '对象', key: 'objects' },
  { title: '操作权限', key: 'ops', width: 280 },
]

const grantRows = computed(() =>
  (authz.value?.grants || []).map((g, i) => ({
    ...g,
    rowKey: `${g.connectionId || 'x'}-${g.scope || ''}-${i}`,
  })),
)

function roleLabel(role?: string | null) {
  if (!role) return '成员'
  return ROLE_LABELS[role] || role
}

function roleColor(role?: string | null) {
  if (role === 'OWNER') return 'gold'
  if (role === 'ADMIN') return 'orange'
  return 'default'
}

function scopeLabel(scope?: string | null) {
  const s = (scope || '').toUpperCase()
  if (s === 'CONNECTION' || s === 'ALL_TABLES') return '整连接'
  if (s === 'DATABASE') return '数据库'
  if (s === 'SCHEMA') return '模式'
  if (s === 'TABLE' || s === 'SPECIFIC_TABLES') return '指定表'
  return scope || '—'
}

function isWideScope(scope?: string | null) {
  const s = (scope || '').toUpperCase()
  return s === 'CONNECTION' || s === 'ALL_TABLES' || s === 'DATABASE' || s === 'SCHEMA'
}

function formatTable(t: { database?: string; schema?: string; name?: string }) {
  const parts = [t.database, t.schema, t.name].filter(Boolean)
  return parts.join('.') || '—'
}

async function loadWorkspaces() {
  listLoading.value = true
  try {
    const resp = await sqlworkApi.listMyWorkspaces()
    workspaces.value = resp.data || []
    if (workspaces.value.length && !selectedId.value) {
      await selectWorkspace(workspaces.value[0].id)
    }
  } finally {
    listLoading.value = false
  }
}

async function selectWorkspace(id: number) {
  selectedId.value = id
  authzLoading.value = true
  authz.value = null
  try {
    const resp = await sqlworkApi.fetchMyAuthz(id)
    authz.value = resp.data || null
  } catch {
    authz.value = null
    message.error('加载空间授权失败')
  } finally {
    authzLoading.value = false
  }
}

function enter() {
  if (!selectedId.value) {
    message.warning('请选择工作空间')
    return
  }
  router.push(`/sqlwork/workspace/${selectedId.value}`)
}

onMounted(loadWorkspaces)
</script>

<style scoped>
.pick-layout {
  display: flex;
  height: calc(100vh - 56px);
  min-height: 420px;
  background: #f5f5f5;
}
.pick-side {
  width: 280px;
  flex: 0 0 280px;
  background: #fafafa;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.side-hd {
  padding: 14px 16px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
}
.side-body {
  flex: 1;
  overflow: auto;
  padding: 8px;
}
.ws-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.ws-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
}
.ws-item:hover {
  background: rgba(0, 0, 0, 0.04);
}
.ws-item.active {
  background: #e6f4ff;
}
.ws-name {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.88);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 6px;
}
.ws-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.pick-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 20px 24px;
  background: #fff;
}
.placeholder {
  max-width: 420px;
  margin: 80px auto;
  text-align: center;
}
.hint {
  margin-top: 12px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}
.panel-hd {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.panel-titles h2 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
}
.panel-sub {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}
.desc {
  margin: 8px 0 0;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}
.section-title {
  font-weight: 600;
  margin: 8px 0 12px;
  font-size: 14px;
}
.conn-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.muted {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.obj-tag {
  margin-bottom: 4px;
}
</style>
