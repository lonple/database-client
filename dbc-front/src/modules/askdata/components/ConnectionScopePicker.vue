<template>
  <div class="scope">
    <a-form-item :label="connectionLabel" required>
      <a-select
        :value="modelValue.connectionId"
        :options="connectionOptions"
        :placeholder="connectionPlaceholder"
        allow-clear
        style="width: 100%"
        @update:value="onConnection"
      />
    </a-form-item>
    <a-form-item label="库" required>
      <a-select
        :value="modelValue.database"
        :options="databaseOptions"
        :loading="loadingDb"
        :disabled="!modelValue.connectionId"
        placeholder="选择库"
        show-search
        allow-clear
        style="width: 100%"
        @update:value="onDatabase"
      />
    </a-form-item>
    <a-form-item v-if="showSchema" label="模式" required>
      <a-select
        :value="modelValue.schema"
        :options="schemaOptions"
        :loading="loadingSchema"
        :disabled="!modelValue.database"
        placeholder="选择模式"
        show-search
        allow-clear
        style="width: 100%"
        @update:value="onSchema"
      />
    </a-form-item>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { isPgStyle } from '@/modules/auth/utils/objectGrant'
import {
  fetchDatabases,
  fetchSchemas,
  type ConnectionSummary,
} from '@/modules/sqlwork/api/sqlwork'

export interface ConnectionScopeValue {
  connectionId?: number
  database?: string
  schema?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: ConnectionScopeValue
    workspaceId: number
    connections: ConnectionSummary[]
    connectionLabel?: string
    connectionPlaceholder?: string
  }>(),
  {
    connectionLabel: '连接',
    connectionPlaceholder: '选择连接',
  },
)

const emit = defineEmits<{
  'update:modelValue': [ConnectionScopeValue]
}>()

const loadingDb = ref(false)
const loadingSchema = ref(false)
const databases = ref<string[]>([])
const schemas = ref<string[]>([])

const connectionOptions = computed(() =>
  props.connections.map((c) => ({
    label: `${c.name}（${c.dbType}）`,
    value: c.connectionId,
  })),
)

const selectedConn = computed(() =>
  props.connections.find((c) => c.connectionId === props.modelValue.connectionId),
)

const showSchema = computed(() =>
  selectedConn.value ? isPgStyle(selectedConn.value.dbType) : false,
)

const databaseOptions = computed(() => databases.value.map((d) => ({ label: d, value: d })))
const schemaOptions = computed(() => schemas.value.map((s) => ({ label: s, value: s })))

function patch(partial: Partial<ConnectionScopeValue>) {
  emit('update:modelValue', { ...props.modelValue, ...partial })
}

async function loadDatabases(connectionId: number) {
  loadingDb.value = true
  databases.value = []
  try {
    const resp = await fetchDatabases(props.workspaceId, connectionId)
    databases.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载库失败')
  } finally {
    loadingDb.value = false
  }
}

async function loadSchemas(connectionId: number, database: string) {
  if (!showSchema.value) {
    schemas.value = []
    return
  }
  loadingSchema.value = true
  schemas.value = []
  try {
    const resp = await fetchSchemas(props.workspaceId, connectionId, database)
    schemas.value = resp.data || []
  } catch (e: any) {
    message.error(e?.message || '加载模式失败')
  } finally {
    loadingSchema.value = false
  }
}

function onConnection(connectionId?: number) {
  patch({ connectionId, database: undefined, schema: undefined })
  schemas.value = []
  databases.value = []
  if (connectionId) loadDatabases(connectionId)
}

function onDatabase(database?: string) {
  const connectionId = props.modelValue.connectionId
  patch({ database, schema: undefined })
  schemas.value = []
  if (connectionId && database && showSchema.value) {
    loadSchemas(connectionId, database)
  }
}

function onSchema(schema?: string) {
  patch({ schema })
}

watch(
  () => [props.modelValue.connectionId, props.workspaceId] as const,
  ([cid]) => {
    if (cid && !databases.value.length) loadDatabases(cid)
  },
  { immediate: true },
)

watch(
  () => [props.modelValue.connectionId, props.modelValue.database, showSchema.value] as const,
  ([cid, db, pg]) => {
    if (cid && db && pg && !schemas.value.length) loadSchemas(cid, db)
  },
)
</script>
