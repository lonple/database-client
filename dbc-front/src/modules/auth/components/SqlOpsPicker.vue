<template>
  <div class="sql-ops-picker">
    <div v-if="showAllToggle" class="ops-all">
      <a-checkbox :checked="allChecked" @change="onToggleAll">
        所有权限（可执行任意 SQL）
      </a-checkbox>
      <span class="ops-hint">勾选后等于授予全部 DML + DDL；取消则清空</span>
    </div>
    <a-alert
      v-else-if="hasAllowedFilter"
      type="info"
      show-icon
      style="margin-bottom: 4px"
      message="可选项已按空间资产授权过滤；空间未授予全部权限时不可勾选「所有权限」。"
    />
    <div v-if="dmlOptions.length" class="ops-block">
      <b>DML</b>
      <a-checkbox-group
        :value="dmlSelected"
        :options="dmlOptions"
        @update:value="onDmlChange"
      />
    </div>
    <div v-if="ddlOptions.length" class="ops-block">
      <b>DDL</b>
      <a-checkbox-group
        :value="ddlSelected"
        :options="ddlOptions"
        @update:value="onDdlChange"
      />
    </div>
    <div v-if="!availableOps.length" class="ops-empty">当前所选对象在空间资产中无可分配的 SQL 权限</div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { CheckboxChangeEvent } from 'ant-design-vue/es/checkbox/interface'
import { DDL_OPS, DML_OPS } from '@/modules/sqlwork/constants'
import { ALL_SQL_OPS } from '@/modules/auth/utils/sqlOps'

/** DML / DDL 可同时多选；「所有权限」仅在可选全集且全选时为勾选态。 */
const DML_SET = new Set<string>(DML_OPS)
const DDL_SET = new Set<string>(DDL_OPS)

const props = defineProps<{
  modelValue: string[]
  /** 可选权限上限；不传则等同全部 DML+DDL（资产授权场景） */
  allowedOps?: string[] | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

function normalizeAllowed(input?: string[] | null): string[] {
  if (input == null) return [...ALL_SQL_OPS]
  const set = new Set(input.map((s) => String(s).toUpperCase()))
  return ALL_SQL_OPS.filter((op) => set.has(op))
}

const availableOps = computed(() => normalizeAllowed(props.allowedOps))
const availableSet = computed(() => new Set(availableOps.value))
const hasAllowedFilter = computed(() => props.allowedOps != null)
/** 仅当可选集合等于产品全量 SQL 权限时才展示「所有权限」 */
const showAllToggle = computed(() => availableOps.value.length === ALL_SQL_OPS.length)

const dmlOptions = computed(() =>
  DML_OPS.filter((v) => availableSet.value.has(v)).map((v) => ({ label: v, value: v })),
)
const ddlOptions = computed(() =>
  DDL_OPS.filter((v) => availableSet.value.has(v)).map((v) => ({ label: v, value: v })),
)

function normalizeList(input: unknown, allowed: Set<string>): string[] {
  if (!Array.isArray(input)) return []
  const set = new Set(
    input.map((s) => String(s).toUpperCase()).filter((s) => allowed.has(s)),
  )
  return [...allowed].filter((op) => set.has(op))
}

const normalized = computed(() => {
  const set = new Set((props.modelValue || []).map((s) => String(s).toUpperCase()))
  return availableOps.value.filter((op) => set.has(op))
})

const dmlSelected = computed(() => normalized.value.filter((op) => DML_SET.has(op)))
const ddlSelected = computed(() => normalized.value.filter((op) => DDL_SET.has(op)))

/** 仅全部可选权限选中才勾选；部分选中保持未勾选（不用 indeterminate） */
const allChecked = computed(
  () => availableOps.value.length > 0 && normalized.value.length === availableOps.value.length,
)

function emitMerged(nextDml: string[], nextDdl: string[]) {
  const set = new Set<string>([...nextDml, ...nextDdl])
  emit(
    'update:modelValue',
    availableOps.value.filter((op) => set.has(op)),
  )
}

function onDmlChange(vals: string[]) {
  emitMerged(normalizeList(vals, new Set(dmlOptions.value.map((o) => o.value))), ddlSelected.value)
}

function onDdlChange(vals: string[]) {
  emitMerged(dmlSelected.value, normalizeList(vals, new Set(ddlOptions.value.map((o) => o.value))))
}

function onToggleAll(e: CheckboxChangeEvent) {
  emit('update:modelValue', e.target.checked ? [...availableOps.value] : [])
}

/** 可选上限变化时，裁掉已选但不在范围内的权限 */
watch(
  availableOps,
  (ops) => {
    const set = new Set(ops)
    const next = (props.modelValue || [])
      .map((s) => String(s).toUpperCase())
      .filter((op) => set.has(op))
    const same =
      next.length === (props.modelValue || []).length &&
      next.every((op, i) => String(props.modelValue[i]).toUpperCase() === op)
    if (!same) {
      emit('update:modelValue', ops.filter((op) => next.includes(op)))
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.sql-ops-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ops-all {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 2px;
}
.ops-hint {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  padding-left: 24px;
}
.ops-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ops-block b {
  font-weight: 600;
}
.ops-empty {
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}
</style>
