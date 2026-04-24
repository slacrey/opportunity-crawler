<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">审计日志</h1>
        <p class="page-subtitle">规则、复核和通知操作记录</p>
      </div>
      <button class="primary-button" type="button" :disabled="audit.loading" @click="refresh">刷新日志</button>
    </div>
    <p v-if="audit.error" class="state-message state-error">{{ audit.error }}</p>
    <DataTableShell title="最近操作">
      <table class="data-table">
        <thead>
          <tr><th>动作</th><th>资源</th><th>操作者</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="log in audit.items" :key="log.id">
            <td>{{ log.action }}</td>
            <td>{{ resourceLabel(log.resource_type, log.resource_id) }}</td>
            <td>{{ log.actor_username || '-' }}</td>
            <td>{{ log.created_at || '-' }}</td>
          </tr>
          <tr v-if="audit.items.length === 0">
            <td colspan="4">{{ audit.loading ? '加载中...' : '暂无审计日志' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import { useAuditStore } from '../stores/audit'

const audit = useAuditStore()

onMounted(() => {
  void refresh()
})

async function refresh() {
  await audit.loadLogs()
}

function resourceLabel(resourceType?: string, resourceId?: string) {
  return [resourceType, resourceId].filter(Boolean).join(' · ') || '-'
}
</script>
