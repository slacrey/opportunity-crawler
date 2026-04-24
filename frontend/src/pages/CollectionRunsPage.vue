<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">采集运行</h1>
        <p class="page-subtitle">运行状态、条目数和失败诊断</p>
      </div>
      <button class="primary-button" type="button" :disabled="runtime.loading" @click="refresh">刷新运行</button>
    </div>
    <p v-if="runtime.error" class="state-message state-error">{{ runtime.error }}</p>
    <DataTableShell title="运行列表">
      <table class="data-table">
        <thead>
          <tr><th>Run ID</th><th>站点</th><th>状态</th><th>条目</th><th>失败类型</th><th>诊断</th></tr>
        </thead>
        <tbody>
          <tr v-for="run in runs" :key="run.run_id">
            <td>{{ run.run_id }}</td>
            <td>{{ run.source_name || run.source_id || '-' }}</td>
            <td><StatusBadge :status="run.status" /></td>
            <td>{{ run.item_count ?? 0 }}</td>
            <td>{{ run.failure_kind || '-' }}</td>
            <td>{{ diagnosticSummary(run.diagnostic_snapshot) }}</td>
          </tr>
          <tr v-if="runs.length === 0">
            <td colspan="6">{{ runtime.loading ? '加载中...' : '暂无运行记录' }}</td>
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
import { useRuntimeStore, type RunState } from '../stores/runtime'

const runtime = useRuntimeStore()
const runs = computed(() => Object.values(runtime.runs))

onMounted(() => {
  void refresh()
})

async function refresh() {
  await runtime.loadRuns()
}

function diagnosticSummary(snapshot: RunState['diagnostic_snapshot']) {
  if (!snapshot || Object.keys(snapshot).length === 0) return '-'
  return JSON.stringify(snapshot)
}
</script>
