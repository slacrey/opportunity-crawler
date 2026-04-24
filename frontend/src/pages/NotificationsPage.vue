<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">通知日志</h1>
        <p class="page-subtitle">钉钉摘要发送记录</p>
      </div>
    </div>
    <DataTableShell title="发送记录">
      <table class="data-table">
        <thead>
          <tr><th>渠道</th><th>模板</th><th>状态</th><th>失败原因</th></tr>
        </thead>
        <tbody>
          <tr><td>dingtalk</td><td>daily_digest</td><td><StatusBadge status="sent" /></td><td>-</td></tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
</script>

