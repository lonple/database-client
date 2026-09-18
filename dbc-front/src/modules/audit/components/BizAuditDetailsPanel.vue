<template>
  <div class="biz-details">
    <!-- 登录 / 退出 -->
    <template v-if="isAuthAction">
      <a-descriptions bordered :column="1" size="small">
        <a-descriptions-item label="账号">{{ authUsername }}</a-descriptions-item>
        <a-descriptions-item label="结果">
          <a-tag :color="authSuccess ? 'success' : 'error'">
            {{ authSuccess ? '成功' : '失败' }}
          </a-tag>
        </a-descriptions-item>
      </a-descriptions>
    </template>

    <!-- 创建：新建内容 -->
    <template v-else-if="action === 'CREATE'">
      <div class="section-hint">新建内容</div>
      <a-descriptions v-if="afterEntries.length" bordered :column="1" size="small">
        <a-descriptions-item v-for="item in afterEntries" :key="item.key" :label="item.label">
          {{ item.value }}
        </a-descriptions-item>
      </a-descriptions>
      <a-empty v-else description="无详细内容" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </template>

    <!-- 更新：变更对照表 -->
    <template v-else-if="action === 'UPDATE'">
      <div class="section-hint">字段变更</div>
      <a-table
        v-if="changeRows.length"
        size="small"
        row-key="field"
        :pagination="false"
        :columns="changeColumns"
        :data-source="changeRows"
      />
      <a-empty v-else description="无字段变更（或仅敏感字段被过滤）" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </template>

    <!-- 删除：对象摘要 -->
    <template v-else-if="action === 'DELETE'">
      <div class="section-hint">删除对象</div>
      <a-descriptions v-if="keysEntries.length" bordered :column="1" size="small">
        <a-descriptions-item v-for="item in keysEntries" :key="item.key" :label="item.label">
          {{ item.value }}
        </a-descriptions-item>
      </a-descriptions>
      <a-empty v-else description="无对象摘要" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </template>

    <!-- 其它 / 附加字段 -->
    <template v-else>
      <a-descriptions v-if="extraEntries.length" bordered :column="1" size="small">
        <a-descriptions-item v-for="item in extraEntries" :key="item.key" :label="item.label">
          {{ item.value }}
        </a-descriptions-item>
      </a-descriptions>
      <a-empty v-else description="无更多详情" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </template>

    <!-- 非标准动作时，若仍有 after/keys 等残留，上面已覆盖；附加扁平字段给 CREATE 等 -->
    <template v-if="showExtraForStructured && extraEntries.length">
      <div class="section-hint">其它信息</div>
      <a-descriptions bordered :column="1" size="small">
        <a-descriptions-item v-for="item in extraEntries" :key="item.key" :label="item.label">
          {{ item.value }}
        </a-descriptions-item>
      </a-descriptions>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Empty } from 'ant-design-vue'
import {
  entriesOf,
  objectEntries,
  parseChangeRows,
} from '@/modules/audit/utils/formatAudit'

const props = defineProps<{
  action?: string
  details?: Record<string, unknown> | null
}>()

const isAuthAction = computed(() => props.action === 'LOGIN' || props.action === 'LOGOUT')

const authUsername = computed(() => {
  const v = props.details?.username
  return v == null || v === '' ? '-' : String(v)
})

const authSuccess = computed(() => props.details?.success === true || props.details?.success === 'true')

const afterEntries = computed(() => objectEntries(props.details?.after))
const keysEntries = computed(() => objectEntries(props.details?.keys))
const changeRows = computed(() => parseChangeRows(props.details))
const extraEntries = computed(() => entriesOf(props.details))
const showExtraForStructured = computed(
  () => props.action === 'CREATE' || props.action === 'UPDATE' || props.action === 'DELETE',
)

const changeColumns = [
  { title: '字段', dataIndex: 'fieldLabel', key: 'fieldLabel', width: 140 },
  { title: '变更前', dataIndex: 'before', key: 'before' },
  { title: '变更后', dataIndex: 'after', key: 'after' },
]
</script>

<style scoped>
.section-hint {
  margin: 0 0 8px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}
.biz-details :deep(.ant-table) {
  margin-bottom: 0;
}
</style>
