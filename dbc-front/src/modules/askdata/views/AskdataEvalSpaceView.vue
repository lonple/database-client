<template>
  <div class="eval-layout">
    <aside class="side">
      <div class="side-hd">
        <span>测评工程</span>
        <a-button type="link" size="small" @click="openCreate">新建</a-button>
      </div>
      <a-spin :spinning="projLoading">
        <a-empty v-if="!projLoading && !projects.length" description="暂无测评工程" />
        <div
          v-for="p in projects"
          :key="p.id"
          class="proj"
          :class="{ active: activeId === p.id }"
          @click="selectProject(p)"
        >
          <div class="t">{{ p.name }}</div>
          <div class="d">{{ p.remark || '模板 #' + p.templateId }}</div>
        </div>
      </a-spin>
    </aside>
    <main class="main">
      <div class="bar">
        <div>
          <h3>{{ active?.name || '测评空间' }}</h3>
          <div class="sub">工作空间 #{{ workspaceId }} · 模板用例 + 自定义用例</div>
        </div>
        <a-space>
          <a-button @click="backToSpaces">返回空间切换</a-button>
          <a-button @click="goTasks">任务列表</a-button>
          <a-button type="primary" :disabled="!selectedIds.length" :loading="creatingTask" @click="onCreateTask">
            创建任务（{{ selectedIds.length }}）
          </a-button>
          <a-button v-if="active" danger @click="onDeleteProject">删除工程</a-button>
        </a-space>
      </div>
      <div class="toolbar">
        <a-select
          v-model:value="category"
          allow-clear
          placeholder="分类筛选"
          style="width: 220px"
          :options="categoryOptions"
          @change="loadCases"
        />
        <a-button :disabled="!active" @click="openCustom">自定义用例</a-button>
        <a-button :disabled="!active" @click="loadCases">刷新</a-button>
        <span v-if="selectedIds.length" class="sel-hint">已跨页勾选 {{ selectedIds.length }} 条</span>
      </div>
      <div class="body">
        <a-table
          row-key="id"
          size="small"
          :loading="caseLoading"
          :data-source="cases"
          :pagination="{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t: number) => `共 ${t} 条`,
            onChange: onPage,
          }"
          :row-selection="caseRowSelection"
          :columns="columns"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'scope'">
              <a-tag :color="record.scope === 'TEMPLATE' ? 'default' : 'green'">
                {{ record.scope === 'TEMPLATE' ? '模板' : '自定义' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'govern'">
              <a-tag v-if="record.governSubtype === 'BOARD'" color="blue">BOARD</a-tag>
              <a-tag v-else-if="record.governSubtype === 'HITL_SUPPLEMENT'" color="gold">补全</a-tag>
              <a-tag v-else-if="record.governSubtype === 'HITL_NO_SUPPLEMENT'" color="red">拒补</a-tag>
              <span v-else>-</span>
            </template>
            <template v-else-if="column.key === 'question'">
              <a class="q-link" @click="openCaseDetail(record)">{{ record.question }}</a>
            </template>
            <template v-else-if="column.key === 'requiredCols'">
              {{ formatRequiredColumns(record.compareSpec) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="openCaseDetail(record)">详情</a-button>
                <a-button
                  v-if="record.scope === 'PROJECT_CUSTOM'"
                  type="link"
                  danger
                  size="small"
                  @click="onDeleteCase(record.id)"
                >
                  删除
                </a-button>
              </a-space>
            </template>
          </template>
        </a-table>
      </div>
    </main>

    <a-drawer
      v-model:open="detailOpen"
      width="640"
      :title="detailCase?.caseKey || '用例详情'"
      destroy-on-close
    >
      <template v-if="detailCase">
        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="来源">
            {{ detailCase.scope === 'TEMPLATE' ? '模板' : '自定义' }}
          </a-descriptions-item>
          <a-descriptions-item label="分类">{{ detailCase.category }}</a-descriptions-item>
          <a-descriptions-item label="治理">{{ detailCase.governSubtype || '-' }}</a-descriptions-item>
          <a-descriptions-item label="必须返回字段">
            <template v-if="requiredColumnsOf(detailCase.compareSpec).length">
              <a-tag v-for="c in requiredColumnsOf(detailCase.compareSpec)" :key="c">{{ c }}</a-tag>
            </template>
            <span v-else>-</span>
          </a-descriptions-item>
          <a-descriptions-item label="难度">{{ detailCase.difficulty ?? '-' }}</a-descriptions-item>
          <a-descriptions-item label="启用">{{ detailCase.enabled ? '是' : '否' }}</a-descriptions-item>
          <a-descriptions-item label="标签">
            {{ (detailCase.tags || []).join(', ') || '-' }}
          </a-descriptions-item>
        </a-descriptions>
        <h4 class="detail-h">问题</h4>
        <pre class="detail-pre">{{ detailCase.question }}</pre>
        <h4 class="detail-h">期望 SQL</h4>
        <pre class="detail-pre">{{ detailCase.expectSql || '-' }}</pre>
        <h4 class="detail-h">HITL 补充话术</h4>
        <pre class="detail-pre">{{
          detailCase.hitlReplies?.length ? detailCase.hitlReplies.join('\n') : '-'
        }}</pre>
      </template>
    </a-drawer>

    <a-modal
      v-model:open="createOpen"
      title="新建测评工程"
      ok-text="创建"
      width="560px"
      :confirm-loading="creating"
      @ok="submitCreate"
    >
      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="createForm.name" />
        </a-form-item>
        <a-form-item label="模板" required>
          <a-select v-model:value="createForm.templateId" :options="templateOptions" />
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="createForm.remark" />
        </a-form-item>
        <a-divider orientation="left" plain>数据来源</a-divider>
        <p class="form-hint">探测/生成默认在此作用域（连接 → 库 → 模式由元数据接口加载）。</p>
        <ConnectionScopePicker
          v-model="createForm.source"
          :workspace-id="workspaceId"
          :connections="connections"
          connection-label="来源连接"
          connection-placeholder="选择数据来源连接"
        />
        <a-divider orientation="left" plain>工作连接</a-divider>
        <p class="form-hint">测评自动执行时临时表/结果表落此作用域。</p>
        <ConnectionScopePicker
          v-model="createForm.work"
          :workspace-id="workspaceId"
          :connections="connections"
          connection-label="工作连接"
          connection-placeholder="选择工作连接"
        />
      </a-form>
    </a-modal>

    <a-modal v-model:open="customOpen" title="自定义用例" ok-text="保存" :confirm-loading="savingCustom" @ok="submitCustom">
      <a-form layout="vertical">
        <a-form-item label="分类" required>
          <a-input v-model:value="customForm.category" placeholder="SINGLE_FILTER" />
        </a-form-item>
        <a-form-item label="问题" required>
          <a-textarea v-model:value="customForm.question" :rows="3" />
        </a-form-item>
        <a-form-item label="期望 SQL">
          <a-textarea v-model:value="customForm.expectSql" :rows="4" />
        </a-form-item>
        <a-form-item label="必须返回字段" required>
          <a-select
            v-model:value="customForm.requiredColumns"
            mode="tags"
            placeholder="输入列名后回车，如 dept_name、amt"
            style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="拒答/空结果用例">
          <a-switch v-model:checked="customForm.emptyOrRefuse" />
          <span class="form-hint" style="margin-left: 8px">开启后按 empty_or_refuse 判定，可不填必须字段</span>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { listWorkspaceConnections, type ConnectionSummary } from '@/modules/sqlwork/api/sqlwork'
import ConnectionScopePicker, {
  type ConnectionScopeValue,
} from '@/modules/askdata/components/ConnectionScopePicker.vue'
import { isPgStyle } from '@/modules/auth/utils/objectGrant'
import * as evalApi from '@/modules/askdata/api/eval'
import type { EvalCase, EvalProject, EvalTemplate } from '@/modules/askdata/api/eval'

const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => Number(route.params.workspaceId))

const projects = ref<EvalProject[]>([])
const templates = ref<EvalTemplate[]>([])
const connections = ref<ConnectionSummary[]>([])
const activeId = ref<number | null>(null)
const active = computed(() => projects.value.find((p) => p.id === activeId.value) || null)
const projLoading = ref(false)
const caseLoading = ref(false)
const cases = ref<EvalCase[]>([])
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const category = ref<string | undefined>()
const selectedIds = ref<number[]>([])
const creatingTask = ref(false)

const createOpen = ref(false)
const creating = ref(false)
const createForm = reactive({
  name: '',
  remark: '',
  templateId: undefined as number | undefined,
  source: {} as ConnectionScopeValue,
  work: {} as ConnectionScopeValue,
})

const customOpen = ref(false)
const savingCustom = ref(false)
const customForm = reactive({
  category: 'SINGLE_FILTER',
  question: '',
  expectSql: '',
  requiredColumns: [] as string[],
  emptyOrRefuse: false,
})

const templateOptions = computed(() =>
  templates.value.map((t) => ({ value: t.id, label: `${t.name} (${t.code})` })),
)
const categoryOptions = [
  { value: 'SINGLE_FILTER', label: 'SINGLE_FILTER' },
  { value: 'MULTI_JOIN_FILTER', label: 'MULTI_JOIN_FILTER' },
  { value: 'SINGLE_AGG', label: 'SINGLE_AGG' },
  { value: 'MULTI_JOIN_AGG', label: 'MULTI_JOIN_AGG' },
  { value: 'MULTI_GOVERN_FILTER', label: 'MULTI_GOVERN_FILTER' },
  { value: 'MULTI_GOVERN_AGG', label: 'MULTI_GOVERN_AGG' },
]

const columns = [
  { title: 'case_key', dataIndex: 'caseKey', key: 'caseKey', width: 160 },
  { title: '来源', key: 'scope', width: 90 },
  { title: '分类', dataIndex: 'category', key: 'category', width: 160 },
  { title: '治理', key: 'govern', width: 90 },
  { title: '问题', dataIndex: 'question', key: 'question', ellipsis: true },
  { title: '必须列', key: 'requiredCols', width: 160, ellipsis: true },
  { title: '操作', key: 'action', width: 120 },
]

const detailOpen = ref(false)
const detailCase = ref<EvalCase | null>(null)

function requiredColumnsOf(spec?: Record<string, unknown> | null): string[] {
  if (!spec) return []
  const raw = spec.requiredColumns ?? spec.required_columns ?? spec.columns
  if (!Array.isArray(raw)) return []
  return raw.map((c) => String(c)).filter(Boolean)
}

function formatRequiredColumns(spec?: Record<string, unknown> | null): string {
  const cols = requiredColumnsOf(spec)
  return cols.length ? cols.join(', ') : '-'
}

function openCaseDetail(record: EvalCase) {
  detailCase.value = record
  detailOpen.value = true
}

function applyCaseSelection(
  next: Set<number>,
  records: { id: number }[],
  selected: boolean,
) {
  for (const r of records) {
    const id = Number(r.id)
    if (Number.isNaN(id)) continue
    if (selected) next.add(id)
    else next.delete(id)
  }
}

const caseRowSelection = computed(() => ({
  selectedRowKeys: selectedIds.value,
  preserveSelectedRowKeys: true,
  onSelect(record: EvalCase, selected: boolean) {
    const next = new Set(selectedIds.value)
    applyCaseSelection(next, [record], selected)
    selectedIds.value = [...next]
  },
  onSelectAll(selected: boolean, _rows: EvalCase[], changeRows: EvalCase[]) {
    const next = new Set(selectedIds.value)
    applyCaseSelection(next, changeRows || [], selected)
    selectedIds.value = [...next]
  },
}))

function onPage(p: number, ps: number) {
  page.value = p
  pageSize.value = ps
  loadCases()
}

function validateScope(label: string, scope: ConnectionScopeValue): string | null {
  if (!scope.connectionId) return `请选择${label}连接`
  if (!scope.database?.trim()) return `请选择${label}库`
  const conn = connections.value.find((c) => c.connectionId === scope.connectionId)
  if (conn && isPgStyle(conn.dbType) && !scope.schema?.trim()) {
    return `请选择${label}模式`
  }
  return null
}

async function loadProjects() {
  projLoading.value = true
  try {
    const resp = await evalApi.listEvalProjects(workspaceId.value)
    projects.value = resp.data || []
    if (!activeId.value && projects.value.length) {
      activeId.value = projects.value[0].id
    }
  } catch (e: any) {
    message.error(e?.message || '加载测评工程失败')
  } finally {
    projLoading.value = false
  }
}

async function loadCases() {
  if (!activeId.value) {
    cases.value = []
    total.value = 0
    return
  }
  caseLoading.value = true
  try {
    const resp = await evalApi.listEvalCases(activeId.value, {
      category: category.value,
      page: page.value,
      pageSize: pageSize.value,
    })
    cases.value = resp.data?.items || []
    total.value = resp.data?.total || 0
  } catch (e: any) {
    message.error(e?.message || '加载用例失败')
  } finally {
    caseLoading.value = false
  }
}

function selectProject(p: EvalProject) {
  activeId.value = p.id
  selectedIds.value = []
  page.value = 1
  loadCases()
}

async function openCreate() {
  createForm.name = ''
  createForm.remark = ''
  createForm.source = {}
  createForm.work = {}
  createOpen.value = true
  if (!templates.value.length) {
    const t = await evalApi.listEvalTemplates()
    templates.value = t.data || []
  }
  if (!connections.value.length) {
    const c = await listWorkspaceConnections(workspaceId.value)
    connections.value = c.data || []
  }
  if (!createForm.templateId && templates.value.length) {
    createForm.templateId = templates.value[0].id
  }
}

async function submitCreate() {
  if (!createForm.name?.trim() || !createForm.templateId) {
    message.warning('请填写名称与模板')
    return
  }
  const sourceErr = validateScope('数据来源', createForm.source)
  if (sourceErr) {
    message.warning(sourceErr)
    return
  }
  const workErr = validateScope('工作', createForm.work)
  if (workErr) {
    message.warning(workErr)
    return
  }
  const sourceConn = connections.value.find((c) => c.connectionId === createForm.source.connectionId)
  const workConn = connections.value.find((c) => c.connectionId === createForm.work.connectionId)
  creating.value = true
  try {
    const resp = await evalApi.createEvalProject({
      workspaceId: workspaceId.value,
      name: createForm.name.trim(),
      remark: createForm.remark || undefined,
      templateId: createForm.templateId,
      sourceConnectionId: createForm.source.connectionId!,
      sourceDatabase: createForm.source.database!,
      sourceSchema: sourceConn && isPgStyle(sourceConn.dbType) ? createForm.source.schema : undefined,
      workConnectionId: createForm.work.connectionId!,
      workDatabase: createForm.work.database!,
      workSchema: workConn && isPgStyle(workConn.dbType) ? createForm.work.schema : undefined,
    })
    message.success('已创建')
    createOpen.value = false
    await loadProjects()
    if (resp.data?.id) {
      activeId.value = resp.data.id
      await loadCases()
    }
  } catch (e: any) {
    message.error(e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

function openCustom() {
  if (!activeId.value) return
  customOpen.value = true
}

async function submitCustom() {
  if (!activeId.value || !customForm.question) {
    message.warning('请填写必填项')
    return
  }
  if (!customForm.emptyOrRefuse && !customForm.requiredColumns.length) {
    message.warning('请填写必须返回字段')
    return
  }
  savingCustom.value = true
  try {
    const required = customForm.requiredColumns.map((c) => c.trim()).filter(Boolean)
    await evalApi.createEvalCase(activeId.value, {
      category: customForm.category,
      question: customForm.question,
      expectSql: customForm.expectSql || undefined,
      compareMode: customForm.emptyOrRefuse ? 'empty_or_refuse' : 'order_by',
      compareSpec: required.length ? { requiredColumns: required, columns: required } : {},
    })
    message.success('已添加')
    customOpen.value = false
    customForm.question = ''
    customForm.expectSql = ''
    customForm.requiredColumns = []
    customForm.emptyOrRefuse = false
    await loadCases()
  } catch (e: any) {
    message.error(e?.message || '保存失败')
  } finally {
    savingCustom.value = false
  }
}

async function onDeleteCase(id: number) {
  try {
    await evalApi.deleteEvalCase(id)
    message.success('已删除')
    await loadCases()
  } catch (e: any) {
    message.error(e?.message || '删除失败')
  }
}

function onDeleteProject() {
  if (!activeId.value) return
  Modal.confirm({
    title: '删除测评工程？',
    content: '将删除工程与自定义用例；模板用例保留。RUNNING 任务存在时不可删。',
    async onOk() {
      await evalApi.deleteEvalProject(activeId.value!)
      message.success('已删除')
      activeId.value = null
      await loadProjects()
      await loadCases()
    },
  })
}

async function onCreateTask() {
  if (!activeId.value || !selectedIds.value.length) return
  creatingTask.value = true
  try {
    const resp = await evalApi.createEvalTask({
      projectId: activeId.value,
      caseIds: selectedIds.value,
    })
    message.success('任务已创建')
    if (resp.data?.id) {
      router.push({
        name: 'askdata-eval-task-detail',
        params: { workspaceId: String(workspaceId.value), taskId: String(resp.data.id) },
      })
    }
  } catch (e: any) {
    message.error(e?.message || '创建任务失败')
  } finally {
    creatingTask.value = false
  }
}

function goTasks() {
  router.push({
    name: 'askdata-eval-tasks',
    params: { workspaceId: String(workspaceId.value) },
    query: activeId.value ? { projectId: String(activeId.value) } : {},
  })
}

function backToSpaces() {
  router.push({ name: 'askdata-spaces' })
}

onMounted(async () => {
  await loadProjects()
  await loadCases()
})
</script>

<style scoped>
.eval-layout {
  display: flex;
  height: 100%;
  background: #f5f5f5;
}
.side {
  width: 280px;
  background: #fafafa;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}
.side-hd {
  padding: 12px 14px;
  border-bottom: 1px solid #f0f0f0;
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}
.proj {
  margin: 4px 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
}
.proj:hover {
  background: #00000008;
}
.proj.active {
  background: #e6f4ff;
  border-color: #91caff;
}
.proj .t {
  font-weight: 600;
}
.proj .d {
  margin-top: 4px;
  font-size: 12px;
  color: #8c8c8c;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.bar {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.bar h3 {
  margin: 0;
  font-size: 15px;
}
.sub {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
}
.toolbar {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  gap: 8px;
  align-items: center;
}
.sel-hint {
  font-size: 12px;
  color: #8c8c8c;
}
.body {
  flex: 1;
  overflow: auto;
  padding: 12px 16px;
}
.form-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.5;
}
.detail-h {
  margin: 16px 0 8px;
  font-size: 13px;
  font-weight: 600;
}
.detail-pre {
  margin: 0;
  padding: 10px 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
  max-height: 280px;
  overflow: auto;
}
.q-link {
  color: #1677ff;
  cursor: pointer;
}
.q-link:hover {
  text-decoration: underline;
}
</style>
