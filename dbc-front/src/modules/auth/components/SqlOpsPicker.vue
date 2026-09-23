<template>
  <div class="sql-ops-picker">
    <div v-if="showAllToggle" class="ops-all">
      <a-checkbox :checked="anyChecked" @change="onToggleAny">
        所有权限（任意 SQL）
      </a-checkbox>
      <span class="ops-hint">
        含未在下列枚举中的语句（如解析为 OTHER 的指令）；不等于勾选全部 DML/DDL。
      </span>
    </div>
    <a-alert
      v-else-if="hasAllowedFilter"
      type="info"
      show-icon
      style="margin-bottom: 4px"
      message="可选项已按空间资产授权过滤；空间未授予「任意 SQL」时不可勾选「所有权限」。"
    />
    <div v-if="dmlOptions.length" class="ops-block">
      <b>DML</b>
      <a-checkbox-group
        :value="dmlSelected"
        :options="dmlOptions"
        :disabled="anyChecked"
        @update:value="onDmlChange"
      />
    </div>
    <div v-if="ddlOptions.length" class="ops-block">
      <b>DDL</b>
      <a-checkbox-group
        :value="ddlSelected"
        :options="ddlOptions"
        :disabled="anyChecked"
        @update:value="onDdlChange"
      />
    </div>
    <div v-if="!availableNamedOps.length && !showAllToggle" class="ops-empty">
      当前所选对象在空间资产中无可分配的 SQL 权限
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { CheckboxChangeEvent } from 'ant-design-vue/es/checkbox/interface'
import { DDL_OPS, DML_OPS } from '@/modules/sqlwork/constants'
import {
  ALL_SQL_OPS,
  SQL_OP_ANY,
  includesAnyOp,
  normalizeSqlOps,
} from '@/modules/auth/utils/sqlOps'

const DML_SET = new Set<string>(DML_OPS)
const DDL_SET = new Set<string>(DDL_OPS)

const props = defineProps<{
  modelValue: string[]
  /**
   * 可选权限上限。
   * - 不传：资产授权 / 全局管控，可选 ANY + 全部具名 ops
   * - 传入：成员授权；仅当含 ANY 时可勾选「所有权限」
   */
  allowedOps?: string[] | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const hasAllowedFilter = computed(() => props.allowedOps != null)
const allowedIncludesAny = computed(() =>
  props.allowedOps == null ? true : includesAnyOp(props.allowedOps),
)
const showAllToggle = computed(() => allowedIncludesAny.value)

function namedFromAllowed(): string[] {
  if (props.allowedOps == null) return [...ALL_SQL_OPS]
  if (includesAnyOp(props.allowedOps)) return [...ALL_SQL_OPS]
  const set = new Set(props.allowedOps.map((s) => String(s).toUpperCase()))
  return ALL_SQL_OPS.filter((op) => set.has(op))
}

const availableNamedOps = computed(() => namedFromAllowed())
const availableNamedSet = computed(() => new Set(availableNamedOps.value))

const dmlOptions = computed(() =>
  DML_OPS.filter((v) => availableNamedSet.value.has(v)).map((v) => ({ label: v, value: v })),
)
const ddlOptions = computed(() =>
  DDL_OPS.filter((v) => availableNamedSet.value.has(v)).map((v) => ({ label: v, value: v })),
)

const anyChecked = computed(() => includesAnyOp(props.modelValue))

const namedSelected = computed(() => {
  if (anyChecked.value) {
    return availableNamedOps.value
  }
  const set = new Set((props.modelValue || []).map((s) => String(s).toUpperCase()))
  return availableNamedOps.value.filter((op) => set.has(op))
})

const dmlSelected = computed(() => namedSelected.value.filter((op) => DML_SET.has(op)))
const ddlSelected = computed(() => namedSelected.value.filter((op) => DDL_SET.has(op)))

function normalizeList(input: unknown, allowed: Set<string>): string[] {
  if (!Array.isArray(input)) return []
  const set = new Set(
    input.map((s) => String(s).toUpperCase()).filter((s) => allowed.has(s)),
  )
  return [...allowed].filter((op) => set.has(op))
}

function emitMerged(nextDml: string[], nextDdl: string[]) {
  const set = new Set<string>([...nextDml, ...nextDdl])
  emit(
    'update:modelValue',
    normalizeSqlOps(availableNamedOps.value.filter((op) => set.has(op))),
  )
}

function onDmlChange(vals: string[]) {
  if (anyChecked.value) return
  emitMerged(normalizeList(vals, new Set(dmlOptions.value.map((o) => o.value))), ddlSelected.value)
}

function onDdlChange(vals: string[]) {
  if (anyChecked.value) return
  emitMerged(dmlSelected.value, normalizeList(vals, new Set(ddlOptions.value.map((o) => o.value))))
}

function onToggleAny(e: CheckboxChangeEvent) {
  emit('update:modelValue', e.target.checked ? [SQL_OP_ANY] : [])
}

/** 可选上限变化时裁剪 */
watch(
  [availableNamedOps, allowedIncludesAny],
  () => {
    const current = props.modelValue || []
    if (includesAnyOp(current)) {
      if (!allowedIncludesAny.value) {
        emit('update:modelValue', [])
      } else if (normalizeSqlOps(current).length !== 1 || current.length !== 1) {
        emit('update:modelValue', [SQL_OP_ANY])
      }
      return
    }
    const set = new Set(availableNamedOps.value)
    const next = normalizeSqlOps(current.filter((op) => set.has(String(op).toUpperCase())))
    const same =
      next.length === current.length &&
      next.every((op, i) => String(current[i]).toUpperCase() === op)
    if (!same) {
      emit('update:modelValue', next)
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
