<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">采集 Agent</h1>
        <p class="page-subtitle">在线实例、容量和心跳</p>
      </div>
      <button class="primary-button" type="button" :disabled="agents.loading" @click="refresh">刷新 Agent</button>
    </div>
    <p v-if="agents.error" class="state-message state-error">{{ agents.error }}</p>
    <DataTableShell title="Agent 实例">
      <table class="data-table">
        <thead>
          <tr><th>Agent</th><th>主机</th><th>状态</th><th>会话</th><th>最近心跳</th></tr>
        </thead>
        <tbody>
          <tr v-for="agent in agents.items" :key="agent.agent_id">
            <td>{{ agent.agent_id }}</td>
            <td>{{ agent.hostname || agent.host_id || '-' }}</td>
            <td><StatusBadge :status="agent.status" /></td>
            <td>{{ agent.active_sessions ?? 0 }} / {{ agent.capacity ?? 0 }}</td>
            <td>{{ agent.last_heartbeat_at || '-' }}</td>
          </tr>
          <tr v-if="agents.items.length === 0">
            <td colspan="5">{{ agents.loading ? '加载中...' : '暂无 Agent' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAgentsStore } from '../stores/agents'

const agents = useAgentsStore()

onMounted(() => {
  void refresh()
})

async function refresh() {
  await agents.loadAgents()
}
</script>
