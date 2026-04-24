<template>
  <main class="page login-page">
    <section class="panel login-panel">
      <h1 class="page-title">智能商机挖掘助手</h1>
      <form class="form-grid" @submit.prevent="submit">
        <label class="field-label">
          用户名
          <input v-model="username" class="field-input" autocomplete="username" />
        </label>
        <label class="field-label">
          密码
          <input v-model="password" class="field-input" type="password" autocomplete="current-password" />
        </label>
        <button class="primary-button" type="submit">登录</button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('admin')
const password = ref('')

async function submit() {
  await auth.login(username.value, password.value)
  await router.push('/')
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

