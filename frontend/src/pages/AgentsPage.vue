<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">采集 Agent</h1>
        <p class="page-subtitle">在线实例、容量和心跳</p>
      </div>
    </div>
    <DataTableShell title="Agent 实例">
      <table class="data-table">
        <thead>
          <tr><th>Agent</th><th>主机</th><th>状态</th><th>会话</th></tr>
        </thead>
        <tbody>
          <tr><td>local-agent</td><td>localhost</td><td><StatusBadge status="connected" /></td><td>0 / 1</td></tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
</script>

