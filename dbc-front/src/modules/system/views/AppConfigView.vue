<template>
  <div class="app-config">
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>系统管理</a-breadcrumb-item>
      <a-breadcrumb-item>应用配置</a-breadcrumb-item>
    </a-breadcrumb>
    <h2 class="page-title">应用配置</h2>
    <div class="split">
      <aside class="left">
        <div class="left-hint">业务模块</div>
        <button
          v-for="m in modules"
          :key="m.key"
          type="button"
          class="mod-item"
          :class="{ active: active === m.key }"
          @click="active = m.key"
        >
          <span class="mod-name">{{ m.label }}</span>
          <span class="mod-desc">{{ m.desc }}</span>
        </button>
      </aside>
      <section class="right">
        <template v-if="active === 'askdata'">
          <div class="panel-head">
            <h3>智能问数</h3>
            <a-button type="primary" :loading="saving" @click="onSave">保存</a-button>
          </div>
          <a-spin :spinning="loading">
            <a-form layout="vertical" class="form">
              <a-form-item label="LLM 提供方" required>
                <a-select v-model:value="form.llmProvider" style="width: 280px">
                  <a-select-option value="qwen">通义千问 (qwen)</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="每日 Token 限额（全站）" required>
                <a-input-number
                  v-model:value="form.dailyTokenLimit"
                  :min="0"
                  :step="10000"
                  style="width: 280px"
                />
                <div class="field-hint">按自然日累计 prompt+completion；0 表示不限制（不推荐）。</div>
              </a-form-item>
              <a-form-item label="并发问数上限" required>
                <a-input-number
                  v-model:value="form.concurrentChatLimit"
                  :min="1"
                  :max="500"
                  style="width: 280px"
                />
                <div class="field-hint">进程内同时处理的 chat 请求数；保存后立即生效。</div>
              </a-form-item>
              <a-form-item label="测评任务用例并发" required>
                <a-input-number
                  v-model:value="form.evalTaskConcurrency"
                  :min="1"
                  :max="200"
                  style="width: 280px"
                />
                <div class="field-hint">
                  单个测评任务内同时跑的用例数（压测可调高）；下次启动任务时生效，进行中的任务不改。
                </div>
              </a-form-item>
            </a-form>
          </a-spin>
        </template>
        <template v-else>
          <a-empty description="请选择左侧模块" />
        </template>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import * as api from '@/modules/system/api/appConfig'

const modules = [
  { key: 'askdata', label: '智能问数', desc: '模型 / 配额 / 并发' },
] as const

type ModKey = (typeof modules)[number]['key']

const active = ref<ModKey>('askdata')
const loading = ref(false)
const saving = ref(false)
const form = reactive({
  llmProvider: 'qwen',
  dailyTokenLimit: 500000,
  concurrentChatLimit: 20,
  evalTaskConcurrency: 20,
})

async function loadAskdata() {
  loading.value = true
  try {
    const res = await api.getAskdataAppConfig()
    const data = res.data
    if (!data) {
      message.error(res.message || '加载问数配置失败')
      return
    }
    form.llmProvider = data.llmProvider || 'qwen'
    form.dailyTokenLimit = Number(data.dailyTokenLimit ?? 500000)
    form.concurrentChatLimit = Number(data.concurrentChatLimit ?? 20)
    form.evalTaskConcurrency = Number(data.evalTaskConcurrency ?? 20)
  } catch (e: unknown) {
    message.error(e instanceof Error ? e.message : '加载问数配置失败')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (active.value !== 'askdata') return
  saving.value = true
  try {
    const res = await api.putAskdataAppConfig({
      llmProvider: form.llmProvider,
      dailyTokenLimit: form.dailyTokenLimit,
      concurrentChatLimit: form.concurrentChatLimit,
      evalTaskConcurrency: form.evalTaskConcurrency,
    })
    if (!res.data) {
      message.error(res.message || '保存失败')
      return
    }
    form.llmProvider = res.data.llmProvider
    form.dailyTokenLimit = res.data.dailyTokenLimit
    form.concurrentChatLimit = res.data.concurrentChatLimit
    form.evalTaskConcurrency = res.data.evalTaskConcurrency
    message.success('已保存')
  } catch (e: unknown) {
    message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

watch(active, (k) => {
  if (k === 'askdata') void loadAskdata()
})

onMounted(() => {
  void loadAskdata()
})
</script>

<style scoped>
.page-title {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 600;
}
.split {
  display: flex;
  gap: 0;
  min-height: 420px;
  border: 1px solid var(--ant-color-border, #e5e7eb);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.left {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #e5e7eb);
  background: #fafafa;
  padding: 12px 8px;
}
.left-hint {
  font-size: 12px;
  color: #8c8c8c;
  padding: 4px 10px 10px;
}
.mod-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  margin-bottom: 4px;
}
.mod-item:hover {
  background: #f0f0f0;
}
.mod-item.active {
  background: #e6f4ff;
}
.mod-name {
  font-weight: 600;
  color: #1f1f1f;
}
.mod-desc {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
}
.right {
  flex: 1;
  padding: 20px 24px;
  min-width: 0;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-head h3 {
  margin: 0;
  font-size: 16px;
}
.form {
  max-width: 520px;
}
.field-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.4;
}
</style>
