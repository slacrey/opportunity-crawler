<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知日志</h1>
        <p class="page-subtitle">钉钉摘要发送记录</p>
      </div>
      <button class="primary-button" type="button" :disabled="sendDisabled" data-test="send-digest" @click="sendDigest">
        发送摘要
      </button>
    </div>
    <p v-if="notifications.error" class="state-message state-error">{{ notifications.error }}</p>
    <DataTableShell title="发送记录">
      <table class="data-table">
        <thead>
          <tr><th>渠道</th><th>模板</th><th>状态</th><th>商机数</th><th>失败原因</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="log in notifications.items" :key="log.id">
            <td>{{ log.channel || '-' }}</td>
            <td>{{ log.template || '-' }}</td>
            <td><StatusBadge :status="log.status" /></td>
            <td>{{ log.candidate_ids?.length ?? 0 }}</td>
            <td>{{ log.failure_reason || '-' }}</td>
            <td>{{ log.created_at || '-' }}</td>
          </tr>
          <tr v-if="notifications.items.length === 0">
            <td colspan="6">{{ notifications.loading ? '加载中...' : '暂无通知日志' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'
import { useNotificationsStore } from '../stores/notifications'

const auth = useAuthStore()
const notifications = useNotificationsStore()
const sending = ref(false)
const canSendDigest = computed(() => auth.can('notifications:read'))
const sendDisabled = computed(() => notifications.loading || sending.value || !canSendDigest.value)

onMounted(() => {
  void refresh()
})

async function refresh() {
  await notifications.loadLogs()
}

async function sendDigest() {
  if (sendDisabled.value) return
  sending.value = true
  try {
    await notifications.sendDigest(false)
    await refresh()
  } finally {
    sending.value = false
  }
}
</script>
