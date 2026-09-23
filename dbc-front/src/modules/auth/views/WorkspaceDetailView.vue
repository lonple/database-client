<template>
  <div>
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>权限管控</a-breadcrumb-item>
      <a-breadcrumb-item>
        <router-link to="/manage/auth/workspaces">工作空间授权</router-link>
      </a-breadcrumb-item>
      <a-breadcrumb-item>{{ detail?.name || '详情' }}</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>{{ detail?.name || '工作空间' }}</h2>
      <a-button @click="$router.push('/manage/auth/workspaces')">返回列表</a-button>
    </div>
    <div v-if="detail" class="meta-row">
      <span>所有者用户ID：<b>{{ detail.ownerUserId }}</b></span>
      <span>我的角色：<b>{{ roleLabel(detail.myRole) }}</b></span>
      <span>描述：<b>{{ detail.description || '-' }}</b></span>
    </div>

    <a-spin :spinning="loading">
      <a-tabs v-model:activeKey="tab">
        <a-tab-pane key="assets" tab="资产授权">
          <a-alert
            type="info"
            show-icon
            style="margin-bottom: 12px"
            message="定义本空间可用的资产对象与 SQL 操作权限。成员授权只能在此范围内再分配。"
          />
          <div class="toolbar">
            <a-button v-if="canMutate" type="primary" @click="openAssetModal">新增资产授权</a-button>
          </div>
          <a-table
            row-key="id"
            :columns="assetColumns"
            :data-source="detail?.assets || []"
            :pagination="false"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'scope'">
                <div>{{ scopeLabel(record.objectScope) }}</div>
                <div v-if="objectRefs(record).length" class="hint">{{ formatObjectRefs(objectRefs(record)) }}</div>
              </template>
              <template v-else-if="column.key === 'ops'">
                <a-tag v-for="op in formatSqlOps(record.ops)" :key="op" style="margin-bottom: 4px">{{ op }}</a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space v-if="canMutate" size="small">
                  <a @click="openEditAsset(record)">编辑</a>
                  <a-popconfirm title="确认删除该资产授权？" @confirm="onRemoveAsset(record.id)">
                    <a class="danger">删除</a>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="grants" tab="成员授权">
          <a-alert type="info" show-icon style="margin-bottom: 12px">
            <template #message>成员授权三步向导</template>
            <template #description>
              ① 选择用户 → ② 选择授权对象（元数据勾选，含包含合并）→ ③ 选择 SQL 权限（候选 ⊆ 空间资产；「所有权限」=任意 SQL，仅当空间资产含任意 SQL 时可勾选）。
            </template>
          </a-alert>
          <div class="toolbar">
            <a-button v-if="canMutate" type="primary" @click="openMemberGrantWizard">新增成员授权</a-button>
          </div>

          <div class="section-title">空间成员</div>
          <a-table
            row-key="id"
            :columns="memberColumns"
            :data-source="detail?.members || []"
            :pagination="false"
            size="small"
            style="margin-bottom: 16px"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'user'">
                {{ userLabel(record.userId) }}
              </template>
              <template v-else-if="column.key === 'role'">
                <a-tag :color="roleColor(record.roleCode)">{{ roleLabel(record.roleCode) }}</a-tag>
              </template>
              <template v-else-if="column.key === 'action'">
                <template v-if="record.roleCode === 'OWNER'">
                  <span class="hint">不可移除 / 不可改管理员</span>
                </template>
                <a-space v-else-if="canMutate" size="small">
                  <a v-if="record.roleCode === 'ADMIN'" @click="setRole(record.userId, 'OPERATOR')">
                    取消管理员
                  </a>
                  <a v-else @click="setRole(record.userId, 'ADMIN')">设为管理员</a>
                  <a-popconfirm title="确认移除该成员？" @confirm="onRemoveMember(record.userId)">
                    <a class="danger">移除</a>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>

          <div class="section-title">授权列表</div>
          <a-table
            row-key="id"
            :columns="grantColumns"
            :data-source="detail?.memberGrants || []"
            :pagination="false"
            size="middle"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'user'">
                {{ userLabel(record.userId) }}
              </template>
              <template v-else-if="column.key === 'conn'">
                <template v-if="record.grantMode === 'ALL'">授权全部空间资产（同增同减）</template>
                <template v-else>{{ record.connectionName || record.connectionId }}</template>
              </template>
              <template v-else-if="column.key === 'scope'">
                <template v-if="record.grantMode === 'ALL'">跟随空间</template>
                <template v-else>
                  <div>{{ scopeLabel(record.objectScope) }}</div>
                  <div v-if="objectRefs(record).length" class="hint">{{ formatObjectRefs(objectRefs(record)) }}</div>
                </template>
              </template>
              <template v-else-if="column.key === 'ops'">
                <template v-if="record.grantMode === 'ALL'">跟随各条空间资产权限</template>
                <template v-else>
                  <a-tag v-for="op in formatSqlOps(record.ops)" :key="op" style="margin-bottom: 4px">{{ op }}</a-tag>
                </template>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space v-if="canMutate" size="small">
                  <a
                    v-if="record.grantMode !== 'ALL'"
                    @click="openEditMemberGrant(record)"
                  >
                    编辑
                  </a>
                  <span v-else class="hint">跟随空间</span>
                  <a-popconfirm title="确认删除该成员授权？" @confirm="onRemoveGrant(record.id)">
                    <a class="danger">删除</a>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-spin>

    <!-- 资产授权 -->
    <a-modal
      v-model:open="assetModalOpen"
      :title="editingAssetId ? '编辑资产授权' : '新增资产授权'"
      width="1120px"
      :confirm-loading="saving"
      ok-text="保存"
      @ok="submitAssetGrant"
      destroy-on-close
    >
      <a-alert
        type="info"
        show-icon
        style="margin-bottom: 12px"
        :message="
          editingAssetId
            ? '编辑单条资产：请保持同一连接与同一对象层级；可调整对象列表与 SQL 权限。'
            : '左侧按连接/库/模式/表从元数据勾选并添加；右侧列表展示已选对象（含包含合并）。候选连接受 data-scope 限制。'
        "
      />
      <ObjectGrantPicker
        v-model="assetSelectedObjects"
        :workspace-id="workspaceId"
        :connections="assetConnectionCandidates"
      />
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="权限（SQL 操作）" required>
          <SqlOpsPicker v-model="assetOps" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 成员授权三步向导 / 编辑 -->
    <a-modal
      v-model:open="memberWizardOpen"
      :title="editingGrantId ? '编辑成员授权' : '新增成员授权'"
      width="1120px"
      :footer="null"
      destroy-on-close
    >
      <a-steps :current="memberStepIndex" size="small" style="margin-bottom: 20px">
        <a-step v-if="!editingGrantId" title="选择用户" />
        <a-step title="选择授权对象" />
        <a-step title="选择权限" />
      </a-steps>

      <div v-show="!editingGrantId && wizardStep === 0">
        <a-alert
          type="info"
          show-icon
          style="margin-bottom: 12px"
          message="多选用户；已在空间的账号可继续追加授权；未加入的账号提交时自动加入空间。"
        />
        <a-space style="margin-bottom: 12px">
          <a-input
            v-model:value="userQuery"
            placeholder="账号"
            style="width: 200px"
            allow-clear
            @pressEnter="loadUsers"
          />
          <a-button @click="loadUsers">查询</a-button>
          <span class="hint">已选 {{ wizardUserIds.length }} 人</span>
        </a-space>
        <a-table
          row-key="id"
          size="small"
          :columns="userPickColumns"
          :data-source="userRows"
          :loading="userLoading"
          :row-selection="wizardUserSelection"
          :pagination="userPager"
          @change="onUserTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag v-if="memberUserIds.has(record.id)" color="processing">已在空间</a-tag>
              <a-tag v-else :color="record.status === 1 ? 'success' : 'default'">
                {{ record.status === 1 ? '启用' : '停用' }}
              </a-tag>
            </template>
          </template>
        </a-table>
      </div>

      <div v-show="wizardStep === 1">
        <a-alert
          v-if="editingGrantId"
          type="info"
          show-icon
          style="margin-bottom: 12px"
          :message="`编辑成员：${userLabel(wizardUserIds[0])}；可选对象不得超过空间已授范围。`"
        />
        <a-alert
          v-else
          type="info"
          show-icon
          style="margin-bottom: 12px"
          message="从本空间「资产授权」目标中勾选；可选对象不得超过空间已授范围。宽范围资产（整连接/库/模式）内可再选子集。"
        />
        <ObjectGrantPicker
          v-model="memberSelectedObjects"
          :workspace-id="workspaceId"
          :connections="memberConnectionCandidates"
          :workspace-assets="detail?.assets || []"
          restrict-to-workspace-assets
        />
      </div>

      <div v-show="wizardStep === 2">
        <a-form layout="vertical">
          <a-form-item label="权限（SQL 操作）" required>
            <SqlOpsPicker v-model="memberOps" :allowed-ops="memberAllowedOps" />
          </a-form-item>
        </a-form>
      </div>

      <div class="wizard-footer">
        <a-button v-if="wizardStep > memberFirstStep" @click="wizardStep -= 1">上一步</a-button>
        <a-button v-if="wizardStep < 2" type="primary" @click="wizardNext">下一步</a-button>
        <a-button
          v-if="wizardStep === 2"
          type="primary"
          :loading="saving"
          @click="submitMemberGrantWizard"
        >
          {{ editingGrantId ? '保存' : '完成' }}
        </a-button>
        <a-button style="margin-left: 8px" @click="memberWizardOpen = false">取消</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import * as workspaceApi from '@/modules/auth/api/workspace'
import type { ObjectRef, WorkspaceAsset, WorkspaceDetail, WorkspaceMemberGrant } from '@/modules/auth/api/workspace'
import * as assetApi from '@/modules/manage/api/asset'
import type { ConnectionView } from '@/modules/manage/api/asset'
import * as manageUserApi from '@/modules/auth/api/users'
import type { ManageUserSummary } from '@/modules/auth/api/users'
import ObjectGrantPicker from '@/modules/auth/components/ObjectGrantPicker.vue'
import SqlOpsPicker from '@/modules/auth/components/SqlOpsPicker.vue'
import {
  allowedOpsForSelection,
  grantRecordToSelectedObjects,
  selectedObjectsToTargets,
  type ConnectionCandidate,
  type SelectedGrantObject,
} from '@/modules/auth/utils/objectGrant'
import { ALL_SQL_OPS, formatSqlOps } from '@/modules/auth/utils/sqlOps'
import { ROLE_LABELS } from '@/modules/sqlwork/constants'
import { usePermission } from '@/common/permission/usePermission'
import { useAuthStore } from '@/modules/user-center/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const { hasPermission } = usePermission()

const workspaceId = computed(() => Number(route.params.id))
const loading = ref(false)
const saving = ref(false)
const detail = ref<WorkspaceDetail | null>(null)
const tab = ref('assets')
const userNameMap = ref<Record<number, string>>({})

const canMutate = computed(() => {
  if (hasPermission('auth.workspace.operate')) return true
  const role = detail.value?.myRole
  return role === 'OWNER' || role === 'ADMIN'
})

const memberColumns = [
  { title: '用户', key: 'user' },
  { title: '空间角色', key: 'role', width: 140 },
  { title: '操作', key: 'action', width: 220 },
]
const assetColumns = [
  { title: '连接', dataIndex: 'connectionName', key: 'connectionName' },
  { title: '对象范围', key: 'scope' },
  { title: '权限', key: 'ops' },
  { title: '操作', key: 'action', width: 120 },
]
const grantColumns = [
  { title: '成员', key: 'user', width: 140 },
  { title: '连接', key: 'conn' },
  { title: '对象范围', key: 'scope' },
  { title: '权限', key: 'ops' },
  { title: '操作', key: 'action', width: 140 },
]
const userPickColumns = [
  { title: '账号', dataIndex: 'username', key: 'username' },
  { title: '部门', dataIndex: 'deptName', key: 'deptName' },
  { title: '状态', key: 'status', width: 100 },
]

const memberUserIds = computed(() => new Set((detail.value?.members || []).map((m) => m.userId)))

const allConnections = ref<ConnectionView[]>([])
const assetModalOpen = ref(false)
const editingAssetId = ref<number | null>(null)
const assetSelectedObjects = ref<SelectedGrantObject[]>([])
const assetOps = ref<string[]>(['SELECT'])

const memberWizardOpen = ref(false)
const editingGrantId = ref<number | null>(null)
const wizardStep = ref(0)
const wizardUserIds = ref<number[]>([])
const memberSelectedObjects = ref<SelectedGrantObject[]>([])
const memberOps = ref<string[]>(['SELECT'])

const memberFirstStep = computed(() => (editingGrantId.value ? 1 : 0))
/** Steps 组件展示用下标（编辑时跳过「选择用户」） */
const memberStepIndex = computed(() =>
  editingGrantId.value ? Math.max(0, wizardStep.value - 1) : wizardStep.value,
)

const userQuery = ref('')
const userLoading = ref(false)
const userRows = ref<ManageUserSummary[]>([])
const userPager = reactive({ current: 1, pageSize: 10, total: 0 })

const connectionDbTypeMap = computed(() => {
  const map: Record<number, string> = {}
  for (const c of allConnections.value) {
    map[c.id] = c.dbType
  }
  return map
})

const assetConnectionCandidates = computed<ConnectionCandidate[]>(() =>
  allConnections.value.map((c) => ({ id: c.id, name: c.name, dbType: c.dbType })),
)

const memberConnectionCandidates = computed<ConnectionCandidate[]>(() => {
  const assets = detail.value?.assets || []
  const seen = new Set<number>()
  const list: ConnectionCandidate[] = []
  for (const a of assets) {
    if (seen.has(a.connectionId)) continue
    seen.add(a.connectionId)
    list.push({
      id: a.connectionId,
      name: a.connectionName,
      dbType: connectionDbTypeMap.value[a.connectionId] || 'postgresql',
    })
  }
  return list
})

const wizardUserSelection = computed(() => ({
  selectedRowKeys: wizardUserIds.value,
  getCheckboxProps: (record: ManageUserSummary) => ({
    disabled: record.status !== 1,
  }),
  onChange: (keys: (string | number)[]) => {
    wizardUserIds.value = keys.map(Number)
  },
}))

/** 成员可选 SQL 权限：覆盖资产 ops 交集；含 ANY 时可授任意 SQL */
const memberAllowedOps = computed(() => {
  const assets = detail.value?.assets || []
  const allowed = allowedOpsForSelection(assets, memberSelectedObjects.value)
  const hasAny = allowed.some((o) => String(o).toUpperCase() === 'ANY')
  const set = new Set(allowed.map((o) => o.toUpperCase()))
  const named = ALL_SQL_OPS.filter((op) => set.has(op))
  return hasAny ? ['ANY', ...named] : named
})

function roleLabel(code?: string | null) {
  if (!code) return '-'
  return ROLE_LABELS[code] || code
}

function roleColor(code: string) {
  if (code === 'OWNER') return 'gold'
  if (code === 'ADMIN') return 'success'
  return 'default'
}

function scopeLabel(scope?: string | null) {
  const s = (scope || '').toUpperCase()
  if (s === 'CONNECTION' || s === 'ALL_TABLES') return '整个连接'
  if (s === 'DATABASE') return '指定库'
  if (s === 'SCHEMA') return '指定模式'
  if (s === 'TABLE' || s === 'SPECIFIC_TABLES') return '指定表'
  return scope || '-'
}

function objectRefs(row: { objects?: ObjectRef[]; tables?: ObjectRef[] }) {
  if (row.objects?.length) return row.objects
  return row.tables || []
}

function formatObjectRefs(refs: ObjectRef[]) {
  return refs
    .map((r) => {
      if (r.name) {
        const parts = [r.database, r.schema, r.name].filter(Boolean)
        return parts.join('.')
      }
      if (r.schema) return `${r.database}.${r.schema}`
      if (r.database) return r.database
      return '-'
    })
    .join(', ')
}

function userLabel(userId: number) {
  return userNameMap.value[userId] || `用户#${userId}`
}

async function loadDetail() {
  loading.value = true
  try {
    const resp = await workspaceApi.getWorkspace(workspaceId.value)
    detail.value = resp.data
    await enrichUserNames()
  } finally {
    loading.value = false
  }
}

async function enrichUserNames() {
  const ids = new Set<number>()
  detail.value?.members.forEach((m) => ids.add(m.userId))
  detail.value?.memberGrants.forEach((g) => ids.add(g.userId))
  if (auth.user?.id) {
    userNameMap.value[auth.user.id] = auth.user.username
  }
  if (!ids.size) return
  try {
    const resp = await manageUserApi.fetchUsersForWorkspace({ page: 1, size: 100 })
    for (const u of resp.data?.records || []) {
      userNameMap.value[u.id] = u.username
    }
  } catch {
    /* ignore */
  }
}

async function loadConnections() {
  try {
    const resp = await assetApi.listConnections()
    allConnections.value = resp.data || []
  } catch {
    allConnections.value = []
  }
}

async function loadUsers() {
  userLoading.value = true
  try {
    const resp = await manageUserApi.fetchUsersForWorkspace({
      page: userPager.current,
      size: userPager.pageSize,
      username: userQuery.value.trim() || undefined,
    })
    userRows.value = resp.data?.records || []
    userPager.total = resp.data?.total || 0
    for (const u of userRows.value) {
      userNameMap.value[u.id] = u.username
    }
  } finally {
    userLoading.value = false
  }
}

function onUserTableChange(p: { current?: number; pageSize?: number }) {
  userPager.current = p.current || 1
  userPager.pageSize = p.pageSize || 10
  loadUsers()
}

function openAssetModal() {
  editingAssetId.value = null
  assetSelectedObjects.value = []
  assetOps.value = ['SELECT']
  assetModalOpen.value = true
  void loadConnections()
}

function openEditAsset(record: WorkspaceAsset) {
  editingAssetId.value = record.id
  assetSelectedObjects.value = grantRecordToSelectedObjects({
    connectionId: record.connectionId,
    connectionName: record.connectionName,
    objectScope: record.objectScope,
    objects: record.objects,
    tables: record.tables,
    dbType: connectionDbTypeMap.value[record.connectionId] || 'postgresql',
  })
  assetOps.value = [...(record.ops || [])]
  assetModalOpen.value = true
  void loadConnections()
}

async function submitAssetGrant() {
  if (!assetSelectedObjects.value.length) {
    message.warning('请至少添加一个授权对象')
    return Promise.reject()
  }
  if (!assetOps.value.length) {
    message.warning('请勾选权限')
    return Promise.reject()
  }
  const targets = selectedObjectsToTargets(assetSelectedObjects.value)
  if (!targets.length) {
    message.warning('请配置授权对象')
    return Promise.reject()
  }
  if (editingAssetId.value && targets.length !== 1) {
    message.warning('编辑单条资产时请只保留一组对象（同一连接、同一层级）')
    return Promise.reject()
  }
  saving.value = true
  try {
    if (editingAssetId.value) {
      const t = targets[0]
      await workspaceApi.updateAsset(workspaceId.value, editingAssetId.value, {
        connectionId: t.connectionId,
        objectScope: t.objectScope,
        objects: t.objects,
        ops: assetOps.value,
      })
      message.success('资产授权已更新')
    } else {
      for (const t of targets) {
        await workspaceApi.addAsset(workspaceId.value, {
          connectionId: t.connectionId,
          objectScope: t.objectScope,
          objects: t.objects,
          ops: assetOps.value,
        })
      }
      message.success('已保存')
    }
    assetModalOpen.value = false
    editingAssetId.value = null
    await loadDetail()
  } finally {
    saving.value = false
  }
}

function openMemberGrantWizard() {
  editingGrantId.value = null
  wizardStep.value = 0
  wizardUserIds.value = []
  memberSelectedObjects.value = []
  memberOps.value = ['SELECT']
  userQuery.value = ''
  userPager.current = 1
  memberWizardOpen.value = true
  loadUsers()
  loadConnections()
}

function openEditMemberGrant(record: WorkspaceMemberGrant) {
  if (record.grantMode === 'ALL') {
    message.info('跟随全部空间资产的授权无需编辑对象与权限')
    return
  }
  if (!record.connectionId) {
    message.warning('该授权缺少连接信息，无法编辑')
    return
  }
  editingGrantId.value = record.id
  wizardUserIds.value = [record.userId]
  memberSelectedObjects.value = grantRecordToSelectedObjects({
    connectionId: record.connectionId,
    connectionName: record.connectionName,
    objectScope: record.objectScope,
    objects: record.objects,
    tables: record.tables,
    dbType: connectionDbTypeMap.value[record.connectionId] || 'postgresql',
  })
  memberOps.value = [...(record.ops || [])]
  wizardStep.value = 1
  memberWizardOpen.value = true
  loadConnections()
}

function wizardNext() {
  if (wizardStep.value === 0) {
    if (!wizardUserIds.value.length) {
      message.warning('请至少选择一名用户')
      return
    }
  }
  if (wizardStep.value === 1) {
    if (!memberSelectedObjects.value.length) {
      message.warning('请至少添加一个授权对象')
      return
    }
    if (editingGrantId.value) {
      const targets = selectedObjectsToTargets(memberSelectedObjects.value)
      if (targets.length !== 1) {
        message.warning('编辑单条成员授权时请只保留一组对象（同一连接、同一层级）')
        return
      }
    }
    const allowed = memberAllowedOps.value
    if (!allowed.length) {
      message.warning('所选对象在空间资产中无可分配的 SQL 权限，请调整授权对象或先完善资产授权')
      return
    }
    const set = new Set(allowed)
    memberOps.value = memberOps.value.filter((op) => set.has(String(op).toUpperCase()))
    if (!memberOps.value.length && set.has('SELECT')) {
      memberOps.value = ['SELECT']
    } else if (!memberOps.value.length) {
      memberOps.value = [allowed[0]]
    }
  }
  wizardStep.value += 1
}

async function submitMemberGrantWizard() {
  if (!memberOps.value.length) {
    message.warning('请勾选权限')
    return
  }
  const allowed = memberAllowedOps.value
  if (!allowed.length) {
    message.warning('所选权限超出空间资产授权范围')
    return
  }
  const allowedSet = new Set(allowed.map((o) => String(o).toUpperCase()))
  const spaceHasAny = allowedSet.has('ANY')
  const outOfRange = memberOps.value.some((op) => {
    const u = String(op).toUpperCase()
    if (u === 'ANY') return !spaceHasAny
    // 空间含 ANY 时可授予任意具名 ops
    return !spaceHasAny && !allowedSet.has(u)
  })
  if (outOfRange) {
    message.warning('所选权限超出空间资产授权范围')
    return
  }
  const targets = selectedObjectsToTargets(memberSelectedObjects.value)
  if (!targets.length) {
    message.warning('请配置授权对象')
    return
  }
  if (editingGrantId.value && targets.length !== 1) {
    message.warning('编辑单条成员授权时请只保留一组对象（同一连接、同一层级）')
    return
  }
  saving.value = true
  try {
    if (editingGrantId.value) {
      const t = targets[0]
      await workspaceApi.updateMemberGrant(workspaceId.value, editingGrantId.value, {
        connectionId: t.connectionId,
        objectScope: t.objectScope,
        objects: t.objects,
        ops: memberOps.value,
      })
      message.success('成员授权已更新')
    } else {
      await workspaceApi.batchMemberGrants(workspaceId.value, {
        userIds: wizardUserIds.value,
        targets,
        ops: memberOps.value,
      })
      message.success('成员授权已保存')
    }
    memberWizardOpen.value = false
    editingGrantId.value = null
    await loadDetail()
  } finally {
    saving.value = false
  }
}

async function setRole(userId: number, roleCode: string) {
  await workspaceApi.setMemberRole(workspaceId.value, userId, roleCode)
  message.success('已更新角色')
  await loadDetail()
}

async function onRemoveMember(userId: number) {
  await workspaceApi.removeMember(workspaceId.value, userId)
  message.success('已移除')
  await loadDetail()
}

async function onRemoveAsset(assetId: number) {
  await workspaceApi.removeAsset(workspaceId.value, assetId)
  message.success('已删除')
  await loadDetail()
}

async function onRemoveGrant(grantId: number) {
  await workspaceApi.removeMemberGrant(workspaceId.value, grantId)
  message.success('已删除')
  await loadDetail()
}

watch(
  () => route.params.id,
  () => {
    if (workspaceId.value) loadDetail()
  },
)

onMounted(() => {
  loadDetail()
  loadConnections()
})
</script>

<style scoped>
.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  color: rgba(0, 0, 0, 0.65);
}
.toolbar {
  margin-bottom: 12px;
}
.section-title {
  font-weight: 600;
  margin: 8px 0;
}
.hint {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.danger {
  color: #cf1322;
}
.wizard-footer {
  margin-top: 16px;
  text-align: right;
}
</style>
