<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">审计日志</h1>
        <p class="page-subtitle">规则、复核和通知操作记录</p>
      </div>
    </div>
    <DataTableShell title="最近操作">
      <table class="data-table">
        <thead>
          <tr><th>动作</th><th>资源</th><th>操作者</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr><td>opportunity.review</td><td>candidate</td><td>admin</td><td>2026-04-24</td></tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import DataTableShell from '../components/DataTableShell.vue'
</script>
