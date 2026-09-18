<template>
  <div class="login-page">
    <aside class="brand">
      <h1>DBC 数据库客户端</h1>
      <p>统一连接、执行与审计</p>
    </aside>
    <main class="form-wrap">
      <a-form class="card" layout="vertical" :model="form" @finish="onSubmit">
        <h2>登录账号</h2>
        <a-form-item label="账号" name="username" :rules="[{ required: true, message: '请输入账号' }]">
          <a-input v-model:value="form.username" size="large" autocomplete="username" />
        </a-form-item>
        <a-form-item label="密码" name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" size="large" autocomplete="current-password" />
        </a-form-item>
        <a-button type="primary" html-type="submit" block size="large" :loading="loading">登 录</a-button>
        <p class="hint">默认账号 admin / admin · 超级管理员</p>
      </a-form>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as authApi from '@/modules/user-center/api/auth'
import { useAuthStore } from '@/modules/user-center/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin' })

async function onSubmit() {
  loading.value = true
  try {
    const resp = await authApi.login(form.username, form.password)
    auth.setSession(resp.data.token, resp.data.user)
    message.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    router.replace(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100%;
  display: grid;
  grid-template-columns: 1fr 1.15fr;
}
.brand {
  background: #eef3f9;
  padding: 48px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}
.brand h1 { margin: 0; font-size: 28px; }
.brand p { margin: 0; color: rgba(0,0,0,.45); }
.form-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}
.card { width: 360px; }
.card h2 { margin: 0 0 24px; }
.hint { margin-top: 16px; color: rgba(0,0,0,.45); font-size: 12px; }
@media (max-width: 860px) {
  .login-page { grid-template-columns: 1fr; }
}
</style>
