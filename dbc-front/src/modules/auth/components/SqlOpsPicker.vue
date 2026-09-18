<template>
  <div class="sql-ops-picker">
    <div class="ops-all">
      <a-checkbox :checked="allChecked" @change="onToggleAll">
        所有权限（可执行任意 SQL）
      </a-checkbox>
      <span class="ops-hint">勾选后等于授予全部 DML + DDL；取消则清空</span>
    </div>
    <div class="ops-block">
      <b>DML</b>
      <a-checkbox-group
        :value="dmlSelected"
        :options="dmlOptions"
        @update:value="onDmlChange"
      />
    </div>
    <div class="ops-block">
      <b>DDL</b>
      <a-checkbox-group
        :value="ddlSelected"
        :options="ddlOptions"
        @update:value="onDdlChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CheckboxChangeEvent } from 'ant-design-vue/es/checkbox/interface'
import { DDL_OPS, DML_OPS } from '@/modules/sqlwork/constants'

/** DML / DDL 可同时多选；「所有权限」仅在全选时为勾选态（不做半选，避免误判为已全选）。 */
const ALL_OPS = [...DML_OPS, ...DDL_OPS] as string[]
const DML_SET = new Set<string>(DML_OPS)
const DDL_SET = new Set<string>(DDL_OPS)

const props = defineProps<{
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const dmlOptions = DML_OPS.map((v) => ({ label: v, value: v }))
const ddlOptions = DDL_OPS.map((v) => ({ label: v, value: v }))

function normalizeList(input: unknown, allowed: Set<string>): string[] {
  if (!Array.isArray(input)) return []
  const set = new Set(
    input.map((s) => String(s).toUpperCase()).filter((s) => allowed.has(s)),
  )
  return [...allowed].filter((op) => set.has(op))
}

const normalized = computed(() => {
  const set = new Set((props.modelValue || []).map((s) => String(s).toUpperCase()))
  return ALL_OPS.filter((op) => set.has(op))
})

const dmlSelected = computed(() => normalized.value.filter((op) => DML_SET.has(op)))
const ddlSelected = computed(() => normalized.value.filter((op) => DDL_SET.has(op)))

/** 仅全部选中才勾选；部分选中保持未勾选（不用 indeterminate） */
const allChecked = computed(() => normalized.value.length === ALL_OPS.length)

function emitMerged(nextDml: string[], nextDdl: string[]) {
  const set = new Set<string>([...nextDml, ...nextDdl])
  emit(
    'update:modelValue',
    ALL_OPS.filter((op) => set.has(op)),
  )
}

function onDmlChange(vals: string[]) {
  emitMerged(normalizeList(vals, DML_SET), ddlSelected.value)
}

function onDdlChange(vals: string[]) {
  emitMerged(dmlSelected.value, normalizeList(vals, DDL_SET))
}

function onToggleAll(e: CheckboxChangeEvent) {
  emit('update:modelValue', e.target.checked ? [...ALL_OPS] : [])
}
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
</style>
