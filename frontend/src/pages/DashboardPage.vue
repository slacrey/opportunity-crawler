<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">站点健康、复核队列和 Agent 状态</p>
      </div>
      <button class="primary-button" type="button" @click="sources.loadSources()">刷新数据</button>
    </div>
    <div class="metric-grid">
      <article class="metric-card">
        <div class="metric-label">健康站点</div>
        <div class="metric-value">{{ sources.healthSummary.healthy }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">失败站点</div>
        <div class="metric-value">{{ sources.healthSummary.failed }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">需登录</div>
        <div class="metric-value">{{ sources.healthSummary.loginRequired }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">运行中</div>
        <div class="metric-value">{{ runningCount }}</div>
      </article>
    </div>
    <DataTableShell title="最近采集运行">
      <table class="data-table">
        <thead>
          <tr><th>Run ID</th><th>状态</th><th>条目</th></tr>
        </thead>
        <tbody>
          <tr v-for="run in Object.values(runtime.runs)" :key="run.run_id">
            <td>{{ run.run_id }}</td>
            <td><StatusBadge :status="run.status" /></td>
            <td>{{ run.item_count ?? 0 }}</td>
          </tr>
          <tr v-if="Object.keys(runtime.runs).length === 0">
            <td colspan="3">暂无运行记录</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useRuntimeStore } from '../stores/runtime'
import { useSourcesStore } from '../stores/sources'

const runtime = useRuntimeStore()
const sources = useSourcesStore()
const runningCount = computed(() => Object.values(runtime.runs).filter((run) => run.status === 'started').length)
</script>

