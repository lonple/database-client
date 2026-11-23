<template>
  <div class="kb-page">
    <div class="kb-bar">
      <div>
        <h2>知识库</h2>
        <p class="hint">维护原文列表。问数按分类编码检索已发布内容，例如 METADATA、GENERAL、QUESTION。</p>
      </div>
      <a-space>
        <a-select
          v-model:value="filterCategoryId"
          allow-clear
          placeholder="按分类筛选"
          style="width: 220px"
          :options="categoryOptions"
          @change="loadDocs"
        />
        <a-button @click="openCategoryManager">分类管理</a-button>
        <a-button type="primary" @click="openDoc()">新建原文</a-button>
      </a-space>
    </div>

    <section class="docs">
      <a-table
        row-key="id"
        size="middle"
        :loading="loading"
        :data-source="docs"
        :columns="columns"
        :pagination="{ pageSize: 20 }"
        :locale="{ emptyText: '暂无原文' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'category'">
            {{ categoryLabel(record.categoryId) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a @click="openDoc(record)">编辑</a>
              <a @click="openSlices(record)">切片</a>
              <a v-if="record.status !== 'PUBLISHED'" @click="onPublish(record)">发布</a>
              <a v-else @click="onUnpublish(record)">取消发布</a>
              <a-popconfirm title="确认删除该原文？" @confirm="onDelete(record.id)">
                <a class="danger">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </section>

    <a-modal
      v-model:open="catMgrOpen"
      title="分类管理"
      width="720px"
      :footer="null"
      destroy-on-close
    >
      <div class="cat-toolbar">
        <a-input
          v-model:value="catQuery"
          allow-clear
          placeholder="搜索名称或编码"
          style="width: 220px"
        />
        <a-button type="primary" @click="openCategoryForm()">新建分类</a-button>
      </div>
      <a-table
        row-key="id"
        size="small"
        :data-source="filteredCategories"
        :columns="catColumns"
        :pagination="{ pageSize: 8 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="openCategoryForm(record)">编辑</a>
              <a-popconfirm title="确认删除该分类？" @confirm="onDeleteCategory(record.id)">
                <a class="danger">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-modal>

    <a-modal
      v-model:open="catFormOpen"
      :title="catForm.id ? '编辑分类' : '新建分类'"
      :confirm-loading="saving"
      @ok="saveCategory"
    >
      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="catForm.name" maxlength="128" />
        </a-form-item>
        <a-form-item label="编码" required>
          <a-input
            v-model:value="catForm.code"
            maxlength="64"
            placeholder="如 METADATA"
            :disabled="!!catForm.id"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="docOpen"
      :title="docForm.id ? '编辑原文' : '新建原文'"
      :confirm-loading="saving"
      width="720px"
      @ok="saveDoc"
    >
      <a-form layout="vertical">
        <a-form-item label="分类" required>
          <a-select
            v-model:value="docForm.categoryId"
            placeholder="选择分类"
            :options="categoryOptions"
            :disabled="!!docForm.id"
          />
        </a-form-item>
        <a-form-item label="标题" required>
          <a-input v-model:value="docForm.title" maxlength="256" />
        </a-form-item>
        <a-form-item label="简介" required>
          <a-textarea v-model:value="docForm.summary" :rows="2" maxlength="512" />
        </a-form-item>
        <a-form-item label="正文" required>
          <div class="body-tools">
            <a-upload
              :show-upload-list="false"
              accept=".md,.markdown,text/markdown,text/plain"
              :before-upload="onUploadMd"
            >
              <a-button size="small">上传 Markdown</a-button>
            </a-upload>
            <span class="body-hint">选择 .md 文件，内容填入正文（可再编辑）</span>
          </div>
          <a-textarea v-model:value="docForm.body" :rows="10" placeholder="可直接粘贴，或上传 .md 文件" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-drawer v-model:open="sliceOpen" title="切片" width="720" @close="loadDocs">
      <a-space style="margin-bottom: 12px">
        <a-button :loading="slicing" @click="onSuggest">AI 切片</a-button>
        <a-button type="primary" :loading="saving" @click="saveSlices">保存切片</a-button>
      </a-space>
      <div v-for="(s, i) in slices" :key="i" class="slice">
        <a-input v-model:value="s.title" placeholder="标题（英文表名）" />
        <a-input v-model:value="s.description" placeholder="说明（中文表名）" style="margin-top: 6px" />
        <a-input v-model:value="s.bodySummary" placeholder="简介（字段压缩）" style="margin-top: 6px" />
        <a-textarea v-model:value="s.body" :rows="4" placeholder="正文" style="margin-top: 6px" />
        <a class="danger" @click="slices.splice(i, 1)">删除此片</a>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  knowledgeLibraryApi,
  type CategoryNode,
  type DocumentRow,
  type SliceRow,
} from '@/modules/askdata/api/knowledgeLibrary'

const categories = ref<CategoryNode[]>([])
const filterCategoryId = ref<number | null>(null)
const docs = ref<DocumentRow[]>([])
const loading = ref(false)
const saving = ref(false)
const slicing = ref(false)
const catMgrOpen = ref(false)
const catFormOpen = ref(false)
const catQuery = ref('')
const docOpen = ref(false)
const sliceOpen = ref(false)
const sliceDocId = ref<number | null>(null)
const slices = ref<SliceRow[]>([])
const catForm = reactive({ id: 0, name: '', code: '' })
const docForm = reactive({ id: 0, categoryId: null as number | null, title: '', summary: '', body: '' })

const columns = [
  { title: '标题', dataIndex: 'title' },
  { title: '分类', key: 'category', width: 160 },
  { title: '状态', dataIndex: 'status', width: 120 },
  { title: '切片', dataIndex: 'sliceCount', width: 80 },
  { title: '向量', dataIndex: 'vectorSyncStatus', width: 110 },
  { title: '操作', key: 'action', width: 260 },
]

const catColumns = [
  { title: '名称', dataIndex: 'name' },
  { title: '编码', dataIndex: 'code', width: 160 },
  { title: '操作', key: 'action', width: 140 },
]

const flatCategories = computed(() => {
  const out: CategoryNode[] = []
  const walk = (nodes: CategoryNode[]) => {
    for (const n of nodes || []) {
      out.push(n)
      if (n.children?.length) walk(n.children)
    }
  }
  walk(categories.value)
  return out
})

const categoryOptions = computed(() =>
  flatCategories.value.map((c) => ({
    value: c.id,
    label: `${c.name}（${c.code}）`,
  })),
)

const filteredCategories = computed(() => {
  const q = catQuery.value.trim().toLowerCase()
  if (!q) return flatCategories.value
  return flatCategories.value.filter(
    (c) => c.name.toLowerCase().includes(q) || (c.code || '').toLowerCase().includes(q),
  )
})

function categoryLabel(categoryId?: number | null) {
  if (!categoryId) return '-'
  const hit = flatCategories.value.find((c) => c.id === categoryId)
  return hit ? `${hit.name}` : String(categoryId)
}

async function loadCategories() {
  categories.value = await knowledgeLibraryApi.tree()
}

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await knowledgeLibraryApi.listDocuments(filterCategoryId.value || undefined)
  } finally {
    loading.value = false
  }
}

function openCategoryManager() {
  catQuery.value = ''
  catMgrOpen.value = true
}

function openCategoryForm(row?: CategoryNode) {
  catForm.id = row?.id || 0
  catForm.name = row?.name || ''
  catForm.code = row?.code || ''
  catFormOpen.value = true
}

async function saveCategory() {
  if (!catForm.name.trim()) {
    message.warning('请填写名称')
    return
  }
  if (!catForm.id && !catForm.code.trim()) {
    message.warning('请填写编码')
    return
  }
  saving.value = true
  try {
    if (catForm.id) {
      await knowledgeLibraryApi.renameCategory(catForm.id, catForm.name.trim())
      message.success('已更新分类')
    } else {
      await knowledgeLibraryApi.createCategory({
        name: catForm.name.trim(),
        code: catForm.code.trim(),
      })
      message.success('已创建分类')
    }
    catFormOpen.value = false
    await loadCategories()
  } finally {
    saving.value = false
  }
}

async function onDeleteCategory(id: number) {
  await knowledgeLibraryApi.removeCategory(id)
  message.success('已删除分类')
  if (filterCategoryId.value === id) {
    filterCategoryId.value = null
    await loadDocs()
  }
  await loadCategories()
}

async function openDoc(row?: DocumentRow) {
  if (!row && !flatCategories.value.length) {
    message.warning('请先在分类管理中创建分类')
    return
  }
  docForm.id = row?.id || 0
  docForm.categoryId = row?.categoryId || filterCategoryId.value || flatCategories.value[0]?.id || null
  docForm.title = row?.title || ''
  docForm.summary = ''
  docForm.body = ''
  if (row?.id) {
    const detail = await knowledgeLibraryApi.detail(row.id)
    docForm.title = detail.title || row.title
    docForm.summary = detail.summary || ''
    docForm.body = detail.body || ''
    docForm.categoryId = detail.categoryId || row.categoryId || null
  }
  docOpen.value = true
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error || new Error('读取文件失败'))
    reader.readAsText(file, 'UTF-8')
  })
}

function guessTitleFromMdFile(file: File): string {
  const raw = (file.name || '').replace(/\.(md|markdown)$/i, '').trim()
  return raw.slice(0, 256)
}

function guessSummaryFromMd(body: string): string {
  const lines = body.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  for (const line of lines) {
    if (/^#{1,6}\s+/.test(line)) continue
    const plain = line.replace(/^>\s*/, '').trim()
    if (plain) return plain.slice(0, 512)
  }
  return body.trim().slice(0, 512)
}

async function onUploadMd(file: File) {
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
    docForm.body = text
    if (!docForm.title.trim()) {
      docForm.title = guessTitleFromMdFile(file)
    }
    if (!docForm.summary.trim()) {
      docForm.summary = guessSummaryFromMd(text)
    }
    message.success(`已导入：${file.name}`)
  } catch {
    message.error('读取 Markdown 失败')
  }
  return false
}

async function saveDoc() {
  if (!docForm.categoryId) {
    message.warning('请选择分类')
    return
  }
  if (!docForm.title.trim() || !docForm.summary.trim() || !docForm.body.trim()) {
    message.warning('标题、简介、正文都要填')
    return
  }
  saving.value = true
  try {
    if (docForm.id) {
      await knowledgeLibraryApi.updateDocument(docForm.id, {
        title: docForm.title.trim(),
        summary: docForm.summary.trim(),
        body: docForm.body,
      })
    } else {
      await knowledgeLibraryApi.createDocument({
        title: docForm.title.trim(),
        summary: docForm.summary.trim(),
        body: docForm.body,
        categoryId: docForm.categoryId,
      })
    }
    docOpen.value = false
    await loadDocs()
  } finally {
    saving.value = false
  }
}

async function openSlices(row: DocumentRow) {
  sliceDocId.value = row.id
  const detail = await knowledgeLibraryApi.detail(row.id)
  slices.value = (detail.slices || []).map((s) => ({ ...s }))
  sliceOpen.value = true
}

async function onSuggest() {
  if (!sliceDocId.value) return
  slicing.value = true
  try {
    slices.value = await knowledgeLibraryApi.suggestSlices(sliceDocId.value)
  } finally {
    slicing.value = false
  }
}

async function saveSlices() {
  if (!sliceDocId.value) return
  saving.value = true
  try {
    slices.value = await knowledgeLibraryApi.saveSlices(sliceDocId.value, slices.value)
    message.success('切片已保存')
  } finally {
    saving.value = false
  }
}

async function onPublish(row: DocumentRow) {
  await knowledgeLibraryApi.publish(row.id)
  message.success('已发布')
  await loadDocs()
}

async function onUnpublish(row: DocumentRow) {
  await knowledgeLibraryApi.unpublish(row.id)
  message.success('已取消发布')
  await loadDocs()
}

async function onDelete(id: number) {
  await knowledgeLibraryApi.remove(id)
  await loadDocs()
}

onMounted(async () => {
  await loadCategories()
  await loadDocs()
})
</script>

<style scoped>
.kb-page {
  padding: 16px 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.kb-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  gap: 12px;
}
.hint {
  color: #888;
  margin: 4px 0 0;
}
.docs {
  flex: 1;
  background: #fff;
  padding: 8px;
  overflow: auto;
  border: 1px solid #f0f0f0;
}
.cat-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}
.body-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.body-hint {
  color: #999;
  font-size: 12px;
}
.danger {
  color: #cf1322;
}
.slice {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  padding: 10px;
  margin-bottom: 10px;
}
</style>
