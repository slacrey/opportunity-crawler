<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">客户历史</h1>
        <p class="page-subtitle">已接受商机、活动和报价记录</p>
      </div>
    </div>
    <DataTableShell title="客户列表">
      <table class="data-table">
        <thead>
          <tr><th>客户</th><th>地区</th><th>商机</th><th>最近活动</th></tr>
        </thead>
        <tbody>
          <tr><td>昆山某单位</td><td>昆山</td><td>1</td><td>已拜访</td></tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import DataTableShell from '../components/DataTableShell.vue'
</script>

