<template>
  <a-layout class="workbench">
    <a-layout-header class="header">
      <div class="brand" @click="goHome">
        <span class="logo-mark" aria-hidden="true">DBC</span>
        <span class="system-name">数据库客户端</span>
      </div>
      <nav class="nav-l1" aria-label="一级菜单">
        <button
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'home' }"
          @click="goHome"
        >
          首页
        </button>
        <button
          v-if="showSqlworkNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'sqlwork' }"
          @click="goSqlwork"
        >
          SQL 工作台
        </button>
        <button
          v-if="showAuthNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'auth' }"
          @click="goAuth"
        >
          权限管控
        </button>
        <button
          v-if="showManageNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'manage' }"
          @click="goManage"
        >
          资产管理
        </button>
        <button
          v-if="showUserCenterNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'user-center' }"
          @click="goUserCenter"
        >
          用户中心
        </button>
        <button
          v-if="showAuditNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'audit' }"
          @click="goAudit"
        >
          审计日志
        </button>
        <button
          v-if="showSystemNav"
          type="button"
          class="nav-l1-item"
          :class="{ active: topActive === 'system' }"
          @click="goSystem"
        >
          系统管理
        </button>
      </nav>
      <div class="spacer" />
      <template v-if="domain.isPersonal">
        <a-tag color="processing" class="domain-badge">当前：个人空间</a-tag>
        <a-button type="primary" ghost class="exit-personal-btn" @click="onExitPersonal">
          退出个人空间
        </a-button>
      </template>
      <a-dropdown placement="bottomRight">
        <span class="user user-menu-trigger">
          {{ auth.user?.username || '用户' }}
          <span class="caret">▾</span>
        </span>
        <template #overlay>
          <a-menu @click="onUserMenu">
            <a-menu-item v-if="canEnterPersonal && !domain.isPersonal" key="personal">
              个人空间
            </a-menu-item>
            <a-menu-item v-if="domain.isPersonal" key="exit-personal">退出个人空间</a-menu-item>
            <a-menu-divider />
            <a-menu-item key="logout">退出登录</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </a-layout-header>
    <a-layout>
      <a-layout-sider v-if="showSider" width="220" theme="light" class="sider">
        <a-menu
          class="side-menu"
          mode="inline"
          :selected-keys="[selected]"
          @click="onMenu"
          :items="sideMenuItems"
        />
      </a-layout-sider>
      <a-layout-content
        class="content"
        :class="{ 'content-full': !!route.meta.fullContent }"
      >
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/modules/user-center/stores/auth'
import { useDomainStore } from '@/modules/user-center/stores/domain'
import {
  USER_CENTER_ANY_VIEW,
  USER_CENTER_SIDE_MENUS,
  filterMenusByPermission,
  hasAnyPermission,
  hasPermission,
} from '@/common/permission/menu'
import { SYSTEM_SIDE_MENUS } from '@/modules/system/routes'
import { MANAGE_SIDE_MENUS } from '@/modules/manage/routes'
import { AUTH_SIDE_MENUS } from '@/modules/auth/routes'
import { SQLWORK_ANY_VIEW } from '@/modules/sqlwork/routes'
import { AUDIT_ANY_VIEW, AUDIT_SIDE_MENUS } from '@/modules/audit/routes'

const PERSONAL_SPACE_VIEW = 'usercenter.personal.space.view'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const domain = useDomainStore()

const permissions = computed(() => auth.user?.permissions || [])
const isSuperAdmin = computed(() => !!auth.user?.roles?.some((r) => r.code === 'SUPER_ADMIN'))
const canEnterPersonal = computed(() => hasPermission(permissions.value, PERSONAL_SPACE_VIEW))

const showUserCenterNav = computed(
  () => !domain.isPersonal && hasAnyPermission(permissions.value, USER_CENTER_ANY_VIEW),
)
const showSystemNav = computed(() => !domain.isPersonal && isSuperAdmin.value)
const showManageNav = computed(() => {
  if (domain.isPersonal) return canEnterPersonal.value
  return (
    hasPermission(permissions.value, 'manage.instance.view') ||
    hasPermission(permissions.value, 'manage.connection.view')
  )
})
const showAuthNav = computed(() => {
  if (domain.isPersonal) return canEnterPersonal.value
  return (
    hasPermission(permissions.value, 'auth.workspace.view') ||
    hasPermission(permissions.value, 'auth.global.policy.view')
  )
})
const showSqlworkNav = computed(() => hasAnyPermission(permissions.value, SQLWORK_ANY_VIEW))
const showAuditNav = computed(
  () => !domain.isPersonal && hasAnyPermission(permissions.value, AUDIT_ANY_VIEW),
)

const personalLabel = (label: string) => (domain.isPersonal ? `${label}（个人）` : label)

const filteredSideMenus = computed(() => {
  if (topActive.value === 'system') {
    return SYSTEM_SIDE_MENUS
  }
  if (topActive.value === 'auth') {
    const menus = domain.isPersonal
      ? AUTH_SIDE_MENUS.filter((m) => m.key === 'manage-auth-workspaces').map((m) => ({
          ...m,
          label: personalLabel(m.label),
          permission: undefined,
        }))
      : filterMenusByPermission(AUTH_SIDE_MENUS, permissions.value)
    return menus
  }
  if (topActive.value === 'audit') {
    return filterMenusByPermission(AUDIT_SIDE_MENUS, permissions.value)
  }
  if (topActive.value === 'manage') {
    if (domain.isPersonal) {
      return MANAGE_SIDE_MENUS.map((m) => ({
        ...m,
        label: personalLabel(m.label),
        permission: undefined,
      }))
    }
    return filterMenusByPermission(MANAGE_SIDE_MENUS, permissions.value)
  }
  return filterMenusByPermission(USER_CENTER_SIDE_MENUS, permissions.value)
})

const sideMenuItems = computed(() =>
  filteredSideMenus.value.map((m) => ({ key: m.key, label: m.label })),
)

const topActive = computed(() => {
  if (route.path.startsWith('/user-center')) return 'user-center'
  if (route.path.startsWith('/system')) return 'system'
  if (route.path.startsWith('/audit')) return 'audit'
  if (route.path.startsWith('/manage/auth')) return 'auth'
  if (route.path.startsWith('/manage')) return 'manage'
  if (route.path.startsWith('/sqlwork')) return 'sqlwork'
  return 'home'
})

const showSider = computed(
  () =>
    (topActive.value === 'user-center' ||
      topActive.value === 'system' ||
      topActive.value === 'manage' ||
      topActive.value === 'auth' ||
      topActive.value === 'audit') &&
    filteredSideMenus.value.length > 0,
)

const selected = computed(() => {
  if (route.name === 'system-apps') return 'system-apps'
  if (route.name === 'audit-biz-logs') return 'audit-biz-logs'
  if (route.name === 'audit-sql-logs') return 'audit-sql-logs'
  if (route.name === 'manage-instances') return 'manage-instances'
  if (route.name === 'manage-connections') return 'manage-connections'
  if (route.name === 'manage-auth-global-policies') return 'manage-auth-global-policies'
  if (route.name === 'manage-auth-workspaces' || route.name === 'manage-auth-workspace-detail') {
    return 'manage-auth-workspaces'
  }
  if (route.name === 'roles') return 'roles'
  if (route.name === 'depts') return 'depts'
  if (route.name === 'permissions') return 'permissions'
  if (route.name === 'users') return 'users'
  return String(route.name || '')
})

watch(
  () =>
    [
      route.path,
      domain.domain,
      showUserCenterNav.value,
      showSystemNav.value,
      showManageNav.value,
      showAuthNav.value,
      showSqlworkNav.value,
      showAuditNav.value,
      filteredSideMenus.value.map((m) => m.key).join(','),
    ] as const,
  () => {
    if (domain.isPersonal && (route.path.startsWith('/user-center') || route.path.startsWith('/system'))) {
      router.replace('/home')
      return
    }
    if (domain.isPersonal && route.path.startsWith('/audit')) {
      router.replace('/home')
      return
    }
    if (domain.isPersonal && route.path.startsWith('/manage/auth/global-policies')) {
      router.replace('/manage/auth/workspaces')
      return
    }
    if (route.path.startsWith('/system')) {
      if (!showSystemNav.value) {
        router.replace('/home')
        return
      }
      return
    }
    if (route.path.startsWith('/audit')) {
      if (!showAuditNav.value) {
        router.replace('/home')
        return
      }
      const keys = filteredSideMenus.value.map((m) => m.key)
      if (!keys.length) {
        router.replace('/home')
        return
      }
      const routeKey = String(route.name || '')
      if (routeKey && !keys.includes(routeKey)) {
        const first = filteredSideMenus.value[0]
        if (first?.path) router.replace(first.path)
      }
      return
    }
    if (route.path.startsWith('/sqlwork')) {
      if (!showSqlworkNav.value) {
        router.replace('/home')
      }
      return
    }
    if (route.path.startsWith('/manage/auth')) {
      if (!showAuthNav.value) {
        router.replace('/home')
        return
      }
      const keys = filteredSideMenus.value.map((m) => m.key)
      if (!keys.length) {
        router.replace('/home')
        return
      }
      const routeKey =
        route.name === 'manage-auth-workspace-detail'
          ? 'manage-auth-workspaces'
          : String(route.name || '')
      if (routeKey && !keys.includes(routeKey)) {
        const first = filteredSideMenus.value[0]
        if (first?.path) router.replace(first.path)
      }
      return
    }
    if (route.path.startsWith('/manage')) {
      if (!showManageNav.value) {
        router.replace('/home')
        return
      }
      const keys = filteredSideMenus.value.map((m) => m.key)
      if (!keys.length) {
        router.replace('/home')
        return
      }
      const routeKey = String(route.name || '')
      if (routeKey && !keys.includes(routeKey)) {
        const first = filteredSideMenus.value[0]
        if (first?.path) router.replace(first.path)
      }
      return
    }
    if (!route.path.startsWith('/user-center')) return
    if (!showUserCenterNav.value) {
      router.replace('/home')
      return
    }
    const keys = filteredSideMenus.value.map((m) => m.key)
    if (!keys.length) {
      router.replace('/home')
      return
    }
    if (route.name && !keys.includes(String(route.name))) {
      const first = filteredSideMenus.value[0]
      if (first?.path) router.replace(first.path)
    }
  },
  { immediate: true },
)

function goHome() {
  router.push('/home')
}

function goUserCenter() {
  const menus = filterMenusByPermission(USER_CENTER_SIDE_MENUS, permissions.value)
  const first = menus[0]
  router.push(first?.path || '/home')
}

function goSystem() {
  router.push('/system/apps')
}

function goManage() {
  if (domain.isPersonal) {
    router.push('/manage/instances')
    return
  }
  const menus = filterMenusByPermission(MANAGE_SIDE_MENUS, permissions.value)
  const first = menus[0]
  router.push(first?.path || '/manage/instances')
}

function goAuth() {
  if (domain.isPersonal) {
    router.push('/manage/auth/workspaces')
    return
  }
  const menus = filterMenusByPermission(AUTH_SIDE_MENUS, permissions.value)
  const first = menus[0]
  router.push(first?.path || '/manage/auth/global-policies')
}

function goSqlwork() {
  router.push('/sqlwork')
}

function goAudit() {
  const menus = filterMenusByPermission(AUDIT_SIDE_MENUS, permissions.value)
  const first = menus[0]
  router.push(first?.path || '/audit/sql-logs')
}

function onMenu(info: { key: string | number }) {
  const key = String(info.key)
  if (key.startsWith('system-')) {
    const item = SYSTEM_SIDE_MENUS.find((m) => m.key === key)
    router.push(item?.path || '/system/apps')
    return
  }
  if (key.startsWith('audit-')) {
    const item = AUDIT_SIDE_MENUS.find((m) => m.key === key)
    router.push(item?.path || '/audit/sql-logs')
    return
  }
  if (key.startsWith('manage-auth-')) {
    const item = AUTH_SIDE_MENUS.find((m) => m.key === key)
    router.push(item?.path || '/manage/auth/global-policies')
    return
  }
  if (key.startsWith('manage-')) {
    const item = MANAGE_SIDE_MENUS.find((m) => m.key === key)
    router.push(item?.path || '/manage/instances')
    return
  }
  router.push(`/user-center/${key}`)
}

function onExitPersonal() {
  domain.exitPersonal()
  router.push('/home')
}

function onUserMenu(info: { key: string | number }) {
  const key = String(info.key)
  if (key === 'personal') {
    domain.enterPersonal()
    router.push('/home')
    return
  }
  if (key === 'exit-personal') {
    onExitPersonal()
    return
  }
  if (key === 'logout') {
    onLogout()
  }
}

async function onLogout() {
  await auth.doLogout()
  router.replace('/login')
}
</script>

<style scoped>
.workbench { min-height: 100%; }

.header {
  display: flex;
  align-items: stretch;
  gap: 0;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 0 0 16px;
  height: 56px;
  line-height: 56px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 20px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 28px;
  padding: 0 8px;
  border-radius: 6px;
  background: #1677ff;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  line-height: 1;
}

.system-name {
  font-size: 15px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
  white-space: nowrap;
}

.nav-l1 {
  display: flex;
  align-items: stretch;
  height: 100%;
  margin: 0;
  padding: 0;
}

.nav-l1-item {
  appearance: none;
  border: none;
  background: transparent;
  margin: 0;
  padding: 0 20px;
  height: 100%;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
  user-select: none;
  position: relative;
  outline: none;
  box-shadow: none;
}

.nav-l1-item:hover {
  color: #1677ff;
  background: rgba(22, 119, 255, 0.04);
}

.nav-l1-item.active {
  color: #1677ff;
  font-weight: 600;
  background: transparent;
}

.nav-l1-item.active::after {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  background: #1677ff;
}

.spacer { flex: 1; }

.domain-badge {
  align-self: center;
  margin-right: 8px;
  line-height: 22px;
}

.exit-personal-btn {
  align-self: center;
  margin-right: 12px;
  height: 32px;
}

.user {
  color: rgba(0, 0, 0, 0.65);
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  user-select: none;
}

.user-menu-trigger {
  cursor: pointer;
  height: 100%;
}

.user-menu-trigger:hover {
  color: #1677ff;
}

.caret {
  font-size: 12px;
  opacity: 0.65;
}

.sider {
  border-right: 1px solid #f0f0f0;
}

.side-menu {
  border-inline-end: none !important;
  user-select: none;
}

.side-menu :deep(.ant-menu-item),
.side-menu :deep(.ant-menu-submenu-title) {
  cursor: pointer !important;
  user-select: none;
}

.side-menu :deep(.ant-menu-title-content) {
  cursor: pointer !important;
  user-select: none;
}

.content {
  padding: 16px 24px;
  background: #f5f5f5;
  min-height: calc(100vh - 56px);
}

.content-full {
  padding: 0;
  height: calc(100vh - 56px);
  max-height: calc(100vh - 56px);
  overflow: hidden;
  min-height: 0;
}
</style>
