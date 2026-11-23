<template>
  <div class="kb-page">
    <div class="kb-bar">
      <div>
        <h2>库表关系</h2>
        <p class="hint">维护知识图谱。问数固定使用编码为 default 的图谱查询表关联。</p>
      </div>
      <a-space>
        <a-button @click="openImport">导入关系 MD</a-button>
        <a-button type="primary" @click="openCreate">新建图谱</a-button>
      </a-space>
    </div>
    <a-table row-key="id" size="middle" :loading="loading" :data-source="rows" :columns="columns" :pagination="{ pageSize: 20 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-space>
            <a @click="openCanvas(record.id)">画布</a>
            <a @click="openEdit(record)">编辑</a>
            <a-popconfirm title="确认删除该图谱？" @confirm="onDelete(record.id)">
              <a class="danger">删除</a>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="open" :title="form.id ? '编辑图谱' : '新建图谱'" :confirm-loading="saving" @ok="submit">
      <a-form layout="vertical">
        <a-form-item label="编码" required>
          <a-input v-model:value="form.code" maxlength="64" placeholder="default" />
        </a-form-item>
        <a-form-item label="名称" required>
          <a-input v-model:value="form.name" maxlength="256" />
        </a-form-item>
        <a-form-item label="简介" required>
          <a-textarea v-model:value="form.summary" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="importOpen"
      title="导入关系 Markdown"
      :confirm-loading="importing"
      ok-text="开始导入"
      @ok="submitImport"
    >
      <a-form layout="vertical">
        <a-form-item label="Markdown 文件" required>
          <a-upload :before-upload="onPickMd" :show-upload-list="false" accept=".md,.markdown,text/markdown">
            <a-button>选择 .md</a-button>
          </a-upload>
          <span v-if="importForm.fileName" class="file-name">{{ importForm.fileName }}</span>
          <p class="hint">
            推荐使用
            <code>scripts/demo-company/metadata/table-relations.import.md</code>
            （子表|子列|父表|父列）。也兼容现有 table-relations.md 表格。
          </p>
        </a-form-item>
        <a-form-item label="编码（可覆盖 MD）">
          <a-input v-model:value="importForm.code" maxlength="64" placeholder="默认读 MD，缺省 default" />
        </a-form-item>
        <a-form-item label="名称（可覆盖 MD）">
          <a-input v-model:value="importForm.name" maxlength="256" />
        </a-form-item>
        <a-form-item label="简介（可覆盖 MD）">
          <a-textarea v-model:value="importForm.summary" :rows="2" />
        </a-form-item>
        <a-form-item>
          <a-checkbox v-model:checked="importForm.force">编码已存在时强制覆盖重建</a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { graphApi, type GraphRow } from '@/modules/askdata/api/graph'

const router = useRouter()
const rows = ref<GraphRow[]>([])
const loading = ref(false)
const saving = ref(false)
const open = ref(false)
const form = reactive({ id: 0, code: '', name: '', summary: '' })

const importOpen = ref(false)
const importing = ref(false)
const importForm = reactive({
  fileName: '',
  markdown: '',
  code: '',
  name: '',
  summary: '',
  force: true,
})

const columns = [
  { title: '编码', dataIndex: 'code', width: 160 },
  { title: '名称', dataIndex: 'name' },
  { title: '简介', dataIndex: 'summary' },
  { title: '操作', key: 'action', width: 180 },
]

async function load() {
  loading.value = true
  try {
    rows.value = await graphApi.list()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.id = 0
  form.code = ''
  form.name = ''
  form.summary = ''
  open.value = true
}

function openEdit(row: GraphRow) {
  form.id = row.id
  form.code = row.code
  form.name = row.name
  form.summary = row.summary
  open.value = true
}

function openCanvas(id: number) {
  router.push({ name: 'askdata-graph-editor', params: { graphId: String(id) } })
}

function openImport() {
  importForm.fileName = ''
  importForm.markdown = ''
  importForm.code = 'default'
  importForm.name = ''
  importForm.summary = ''
  importForm.force = true
  importOpen.value = true
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file, 'UTF-8')
  })
}

async function onPickMd(file: File) {
  const name = (file.name || '').toLowerCase()
  if (!name.endsWith('.md') && !name.endsWith('.markdown')) {
    message.warning('请上传 .md / .markdown 文件')
    return false
  }
  try {
    const text = await readFileAsText(file)
    if (!text.trim()) {
      message.warning('文件内容为空')
      return false
    }
    importForm.fileName = file.name
    importForm.markdown = text
    message.success(`已载入：${file.name}`)
  } catch {
    message.error('读取 Markdown 失败')
  }
  return false
}

async function submitImport() {
  if (!importForm.markdown.trim()) {
    message.warning('请先选择关系 Markdown 文件')
    return
  }
  importing.value = true
  try {
    const result = await graphApi.importMd({
      markdown: importForm.markdown,
      code: importForm.code.trim() || undefined,
      name: importForm.name.trim() || undefined,
      summary: importForm.summary.trim() || undefined,
      force: importForm.force,
    })
    importOpen.value = false
    message.success(
      `导入成功：${result.tableCount} 表 / ${result.fkCount} FK → ${result.edgeCount} 边` +
        (result.replaced ? '（已覆盖）' : ''),
    )
    await load()
  } catch (e: unknown) {
    const msg = e && typeof e === 'object' && 'message' in e ? String((e as { message: unknown }).message) : ''
    message.error(msg || '导入失败')
  } finally {
    importing.value = false
  }
}

async function submit() {
  if (!form.code.trim() || !form.name.trim() || !form.summary.trim()) {
    message.warning('编码、名称、简介都要填')
    return
  }
  saving.value = true
  try {
    if (form.id) {
      await graphApi.update(form.id, { code: form.code.trim(), name: form.name.trim(), summary: form.summary.trim() })
    } else {
      await graphApi.create({ code: form.code.trim(), name: form.name.trim(), summary: form.summary.trim() })
    }
    open.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(id: number) {
  await graphApi.remove(id)
  await load()
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.kb-page { padding: 16px 20px; }
.kb-bar { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.hint { color: #888; margin: 4px 0 0; font-size: 12px; }
.file-name { margin-left: 10px; color: #555; }
.danger { color: #cf1322; }
code { font-size: 12px; }
</style>
