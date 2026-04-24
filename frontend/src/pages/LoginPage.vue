<template>
  <main class="page login-page">
    <section class="panel login-panel">
      <h1 class="page-title">智能商机挖掘助手</h1>
      <p v-if="sessionExpired" class="state-message state-error">登录已过期，请重新登录</p>
      <p v-if="auth.error" class="state-message state-error">{{ auth.error }}</p>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field-label">
          用户名
          <input v-model="username" class="field-input" autocomplete="username" />
        </label>
        <label class="field-label">
          密码
          <input v-model="password" class="field-input" type="password" autocomplete="current-password" />
        </label>
        <button class="primary-button" type="submit" :disabled="auth.loading">登录</button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const username = ref('admin')
const password = ref('')
const sessionExpired = computed(() => route.query.expired === '1')

async function submit() {
  if (auth.loading) return
  await auth.login(username.value, password.value)
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  await router.push(redirect)
}
</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
}

.login-panel {
  width: min(420px, calc(100vw - 32px));
}
</style>
