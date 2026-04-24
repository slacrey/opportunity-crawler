<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <div class="brand-block">
        <h1 class="brand-title">智能商机挖掘助手</h1>
        <p class="brand-subtitle">Opportunity Control</p>
      </div>
      <nav class="admin-nav" aria-label="主导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">{{ item.label }}</RouterLink>
      </nav>
    </aside>
    <main class="admin-main">
      <header class="admin-topbar">
        <div class="runtime-strip">
          <StatusBadge status="connected" label="事件通道正常" />
          <span>本地 API / Agent</span>
        </div>
        <button class="secondary-button" type="button">刷新</button>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '../components/StatusBadge.vue'

const navItems = [
  { to: '/', label: '仪表盘' },
  { to: '/sources', label: '站点管理' },
  { to: '/runs', label: '采集运行' },
  { to: '/review', label: '商机复核' },
  { to: '/customers', label: '客户历史' },
  { to: '/goals', label: '目标进度' },
  { to: '/notifications', label: '通知日志' },
  { to: '/agents', label: '采集 Agent' },
  { to: '/audit', label: '审计日志' }
]
</script>

