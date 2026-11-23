<template>
  <div class="doc-detail" v-if="row">
    <div class="bar">
      <a-button type="link" @click="goBack">← 返回列表</a-button>
      <h2>{{ row.name }}</h2>
      <a-space>
        <a-button @click="onDownload">下载原件</a-button>
        <a-button @click="pickReplace">替换源文件</a-button>
        <a-popconfirm title="删除后列表不再展示。确认删除？" @confirm="onDelete">
          <a-button danger>删除</a-button>
        </a-popconfirm>
      </a-space>
    </div>
    <p class="status">
      {{ statusLine }}
    </p>
    <a-alert v-if="row.convertStatus === 'FAILED'" type="error" show-icon :message="row.convertError || '转换失败'" />
    <a-alert
      v-else-if="row.markdownEdited"
      type="warning"
      show-icon
      message="正文已人工修改，与最近一次自动转换可能不一致。"
      style="margin-bottom: 12px"
    />
    <a-form layout="vertical">
      <a-form-item label="名称">
        <a-input v-model:value="nameEdit" maxlength="256" />
      </a-form-item>
      <a-form-item label="Markdown">
        <a-textarea v-model:value="mdEdit" :rows="16" :disabled="busy" />
      </a-form-item>
      <a-space>
        <a-button type="primary" :loading="saving" @click="onSave">保存正文</a-button>
        <a-button v-if="row.convertStatus === 'FAILED'" @click="onRetry">重试转换</a-button>
      </a-space>
    </a-form>
    <input ref="replaceInput" type="file" class="hidden" @change="onReplace" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import {
  deleteAskDocument,
  getAskDocument,
  patchAskDocument,
  replaceAskDocument,
  retryAskDocument,
  type AskDocumentRow,
} from '@/modules/askdata/api/documents'
import { ASKDATA_BASE } from '@/modules/askdata/constants'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const row = ref<AskDocumentRow | null>(null)
const nameEdit = ref('')
const mdEdit = ref('')
const saving = ref(false)
const replaceInput = ref<HTMLInputElement | null>(null)
let timer: number | undefined

const docId = computed(() => Number(route.params.id))
const busy = computed(() => {
  const s = row.value?.convertStatus
  return s === 'QUEUED' || s === 'RUNNING'
})
const statusLine = computed(() => {
  const r = row.value
  if (!r) return ''
  const st = r.convertStatus
  const pipe = r.pipeline === 'IMAGE' ? '图片管线' : '文档管线'
  return `${statusLabel(st)} · ${r.sourceFormat} · ${pipe}`
})

function statusLabel(v?: string) {
  const s = String(v || '').toUpperCase()
  if (s === 'SUCCESS') return '转换成功'
  if (s === 'FAILED') return '转换失败'
  if (s === 'RUNNING') return '转换中'
  if (s === 'QUEUED') return '排队中'
  return v || ''
}

function goBack() {
  router.push({ name: 'askdata-documents' })
}

function apply(d: AskDocumentRow) {
  row.value = d
  nameEdit.value = d.name
  mdEdit.value = d.markdown || ''
}

async function load() {
  const resp = await getAskDocument(docId.value)
  if (resp.data) apply(resp.data)
}

async function onSave() {
  saving.value = true
  try {
    const resp = await patchAskDocument(docId.value, {
      name: nameEdit.value.trim(),
      markdown: mdEdit.value,
    })
    if (resp.data) apply(resp.data)
    message.success('已保存')
  } catch (e: any) {
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function onRetry() {
  try {
    const resp = await retryAskDocument(docId.value)
    if (resp.data) apply(resp.data)
    message.success('已重新排队')
  } catch (e: any) {
    message.error(e?.message || '重试失败')
  }
}

async function onDelete() {
  try {
    await deleteAskDocument(docId.value)
    message.success('已删除')
    goBack()
  } catch (e: any) {
    message.error(e?.message || '删除失败')
  }
}

function pickReplace() {
  replaceInput.value?.click()
}

async function onReplace(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  const overwrite = !!row.value?.markdownEdited
  if (overwrite) {
    Modal.confirm({
      title: '正文已修改',
      content: '新转换结果会覆盖当前 Markdown。确认继续？',
      async onOk() {
        await doReplace(file, true)
      },
    })
    return
  }
  await doReplace(file, false)
}

async function doReplace(file: File, confirmOverwrite: boolean) {
  try {
    const resp = await replaceAskDocument(docId.value, file, confirmOverwrite)
    if (resp.data) apply(resp.data)
    message.success('已替换，正在转换')
  } catch (err: any) {
    message.error(err?.message || '替换失败')
  }
}

async function onDownload() {
  try {
    const resp = await fetch(`${ASKDATA_BASE}/api/documents/${docId.value}/source`, {
      headers: { Authorization: `Bearer ${auth.accessToken}` },
    })
    if (!resp.ok) throw new Error('下载失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.value?.sourceFilename || 'file'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    message.error(e?.message || '下载失败')
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (e: any) {
    message.error(e?.message || '加载失败')
  }
  timer = window.setInterval(() => {
    if (busy.value) void load()
  }, 2500)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.doc-detail {
  padding: 16px 24px 32px;
  overflow: auto;
}
.bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.bar h2 {
  margin: 0;
  flex: 1;
  font-size: 18px;
}
.status {
  color: #00000073;
  margin: 0 0 12px;
}
.hidden {
  display: none;
}
</style>
