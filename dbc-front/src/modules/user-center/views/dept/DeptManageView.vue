<template>
  <div class="dept-page">
    <a-breadcrumb style="margin-bottom: 8px">
      <a-breadcrumb-item>用户中心</a-breadcrumb-item>
      <a-breadcrumb-item>部门管理</a-breadcrumb-item>
    </a-breadcrumb>
    <div class="title-row">
      <h2>部门管理</h2>
    </div>
    <div class="panels">
      <aside class="tree-panel">
        <div class="tree-toolbar">
          <a-button size="small" type="primary" :disabled="!selectedId || !canOperate" @click="openCreateChild">
            新增子部门
          </a-button>
        </div>
        <a-spin :spinning="treeLoading">
          <a-tree
            v-if="treeData.length"
            :tree-data="treeData"
            :field-names="{ title: 'name', key: 'id', children: 'children' }"
            :selected-keys="selectedId ? [selectedId] : []"
            default-expand-all
            @select="onSelect"
          />
          <a-empty v-else description="暂无部门" />
        </a-spin>
      </aside>
      <section class="detail-panel">
        <template v-if="detail">
          <div class="detail-header">
            <h3>部门详情</h3>
            <a-space>
              <a-button v-if="canOperate" type="primary" :loading="saving" @click="submitSave">保存</a-button>
              <a-popconfirm
                v-if="canOperate && !detail.root"
                title="确认删除该部门？"
                @confirm="onDelete"
              >
                <a-button danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </div>
          <a-form layout="vertical" class="detail-form">
            <a-form-item label="部门名称" required>
              <a-input v-model:value="form.name" maxlength="64" :disabled="!canOperate" />
            </a-form-item>
            <a-form-item label="部门描述">
              <a-textarea v-model:value="form.description" :rows="3" maxlength="512" :disabled="!canOperate" />
            </a-form-item>
            <a-form-item label="父部门">
              <a-tree-select
                v-if="!detail.root"
                v-model:value="form.parentId"
                style="width: 100%"
                :tree-data="parentTreeOptions"
                :field-names="{ label: 'name', value: 'id', children: 'children' }"
                tree-default-expand-all
                placeholder="选择父部门"
                :disabled="!canOperate"
              />
              <a-input v-else value="（根部门）" disabled />
            </a-form-item>
            <a-form-item label="层级">
              <span>{{ detail.level }} / 10</span>
            </a-form-item>
          </a-form>
        </template>
        <a-empty v-else description="请选择左侧部门" />
      </section>
    </div>

    <a-modal v-model:open="createOpen" title="新增子部门" @ok="submitCreate" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="父部门">
          <a-input :value="detail?.name" disabled />
        </a-form-item>
        <a-form-item label="部门名称" required>
          <a-input v-model:value="createForm.name" maxlength="64" />
        </a-form-item>
        <a-form-item label="部门描述">
          <a-textarea v-model:value="createForm.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import * as deptApi from '@/modules/user-center/api/dept'
import type { DeptTreeNode, DeptView } from '@/modules/user-center/api/types'
import { usePermission } from '@/common/permission/usePermission'

const { hasPermission } = usePermission()
const canOperate = computed(() => hasPermission('usercenter.dept.operate'))

const treeLoading = ref(false)
const saving = ref(false)
const tree = ref<DeptTreeNode[]>([])
const selectedId = ref<number | null>(null)
const detail = ref<DeptView | null>(null)
const createOpen = ref(false)
const form = reactive({ name: '', description: '', parentId: undefined as number | undefined })
const createForm = reactive({ name: '', description: '' })

const treeData = computed(() => tree.value)

function collectForbiddenIds(nodes: DeptTreeNode[], targetId: number, acc: Set<number> = new Set()): Set<number> {
  for (const n of nodes) {
    if (n.id === targetId) {
      acc.add(n.id)
      const mark = (c: DeptTreeNode) => {
        acc.add(c.id)
        ;(c.children || []).forEach(mark)
      }
      ;(n.children || []).forEach(mark)
    } else {
      collectForbiddenIds(n.children || [], targetId, acc)
    }
  }
  return acc
}

function filterTree(nodes: DeptTreeNode[], forbidden: Set<number>): DeptTreeNode[] {
  return nodes
    .filter((n) => !forbidden.has(n.id))
    .map((n) => ({
      ...n,
      children: filterTree(n.children || [], forbidden),
      disabled: false,
    }))
}

const parentTreeOptions = computed(() => {
  if (!selectedId.value) return tree.value
  const forbidden = collectForbiddenIds(tree.value, selectedId.value)
  return filterTree(tree.value, forbidden)
})

async function loadTree(keepId?: number | null) {
  treeLoading.value = true
  try {
    const resp = await deptApi.fetchDeptTree()
    tree.value = resp.data || []
    const id = keepId ?? selectedId.value ?? tree.value[0]?.id ?? null
    if (id) {
      await selectDept(id)
    } else {
      selectedId.value = null
      detail.value = null
    }
  } finally {
    treeLoading.value = false
  }
}

async function selectDept(id: number) {
  selectedId.value = id
  const resp = await deptApi.fetchDept(id)
  detail.value = resp.data
  form.name = resp.data.name
  form.description = resp.data.description || ''
  form.parentId = resp.data.parentId ?? undefined
}

function onSelect(keys: (string | number)[]) {
  if (!keys.length) return
  selectDept(Number(keys[0]))
}

function openCreateChild() {
  if (!selectedId.value) return
  createForm.name = ''
  createForm.description = ''
  createOpen.value = true
}

async function submitCreate() {
  if (!selectedId.value || !createForm.name.trim()) {
    message.warning('请填写部门名称')
    return
  }
  saving.value = true
  try {
    const resp = await deptApi.createDept({
      name: createForm.name.trim(),
      description: createForm.description || undefined,
      parentId: selectedId.value,
    })
    message.success('已创建')
    createOpen.value = false
    await loadTree(resp.data.id)
  } finally {
    saving.value = false
  }
}

async function submitSave() {
  if (!detail.value || !form.name.trim()) {
    message.warning('请填写部门名称')
    return
  }
  if (!detail.value.root && !form.parentId) {
    message.warning('请选择父部门')
    return
  }
  saving.value = true
  try {
    await deptApi.updateDept(detail.value.id, {
      name: form.name.trim(),
      description: form.description || undefined,
      parentId: detail.value.root ? null : form.parentId,
    })
    message.success('已保存')
    await loadTree(detail.value.id)
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  if (!detail.value || detail.value.root) return
  await deptApi.deleteDept(detail.value.id)
  message.success('已删除')
  selectedId.value = null
  await loadTree(null)
}

onMounted(() => loadTree())
</script>

<style scoped>
.dept-page { height: 100%; }
.title-row { margin-bottom: 12px; }
.title-row h2 { margin: 0; font-size: 20px; }
.panels {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  min-height: 520px;
}
.tree-panel, .detail-panel {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px;
}
.tree-toolbar { margin-bottom: 12px; }
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.detail-header h3 { margin: 0; font-size: 16px; }
.detail-form { max-width: 480px; }
</style>
