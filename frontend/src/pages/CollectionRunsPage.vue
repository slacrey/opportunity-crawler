<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">采集运行</h1>
        <p class="page-subtitle">运行状态、条目数和失败诊断</p>
      </div>
    </div>
    <DataTableShell title="运行列表">
      <table class="data-table">
        <thead>
          <tr><th>Run ID</th><th>站点</th><th>状态</th><th>条目</th><th>诊断</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>run-demo</td>
            <td>中国政府采购网</td>
            <td><StatusBadge status="succeeded" /></td>
            <td>12</td>
            <td>fixture_complete</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
</script>

