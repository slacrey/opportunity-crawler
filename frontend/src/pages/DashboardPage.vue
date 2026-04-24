<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">站点健康、复核队列和 Agent 状态</p>
      </div>
      <button class="primary-button" type="button" :disabled="dashboard.loading || runtime.loading" @click="refresh">
        刷新数据
      </button>
    </div>
    <p v-if="dashboard.error || runtime.error" class="state-message state-error">
      {{ dashboard.error || runtime.error }}
    </p>
    <div class="metric-grid">
      <article class="metric-card">
        <div class="metric-label">站点总数</div>
        <div class="metric-value">{{ summary.sources.total }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">待复核</div>
        <div class="metric-value">{{ summary.opportunities.pending }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">高分商机</div>
        <div class="metric-value">{{ summary.opportunities.high_score }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">Agent 在线</div>
        <div class="metric-value">{{ summary.agents.online }}</div>
      </article>
    </div>
    <div class="metric-grid compact-metrics">
      <article class="metric-card">
        <div class="metric-label">健康站点</div>
        <div class="metric-value">{{ summary.sources.healthy }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">失败站点</div>
        <div class="metric-value">{{ summary.sources.failed }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">需登录</div>
        <div class="metric-value">{{ summary.sources.login_required }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">失败运行</div>
        <div class="metric-value">{{ summary.runs.failed }}</div>
      </article>
    </div>
    <DataTableShell title="最近采集运行">
      <table class="data-table">
        <thead>
          <tr><th>Run ID</th><th>站点</th><th>状态</th><th>条目</th></tr>
        </thead>
        <tbody>
          <tr v-for="run in Object.values(runtime.runs)" :key="run.run_id">
            <td>{{ run.run_id }}</td>
            <td>{{ run.source_name || run.source_id || '-' }}</td>
            <td><StatusBadge :status="run.status" /></td>
            <td>{{ run.item_count ?? 0 }}</td>
          </tr>
          <tr v-if="Object.keys(runtime.runs).length === 0">
            <td colspan="4">{{ runtime.loading ? '加载中...' : '暂无运行记录' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useDashboardStore, type DashboardSummary } from '../stores/dashboard'
import { useRuntimeStore } from '../stores/runtime'

const dashboard = useDashboardStore()
const runtime = useRuntimeStore()
const emptySummary: DashboardSummary = {
  sources: { total: 0, healthy: 0, failed: 0, login_required: 0 },
  opportunities: { pending: 0, accepted: 0, high_score: 0 },
  runs: { running: 0, failed: 0 },
  agents: { online: 0 }
}
const summary = computed(() => dashboard.summary ?? emptySummary)

onMounted(() => {
  void refresh()
})

async function refresh() {
  await Promise.allSettled([dashboard.loadSummary(), runtime.loadRuns()])
}
</script>

<style scoped>
.compact-metrics .metric-value {
  font-size: 22px;
}
</style>
