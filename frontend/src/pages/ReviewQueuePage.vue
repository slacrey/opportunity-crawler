<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">商机复核</h1>
        <p class="page-subtitle">高分候选、证据和跟进状态</p>
      </div>
    </div>
    <DataTableShell title="待复核商机">
      <table class="data-table">
        <thead>
          <tr><th>标题</th><th>客户</th><th>评分</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="candidate in displayedQueue" :key="candidate.id">
            <td>{{ candidate.title }}</td>
            <td>{{ candidate.organization_name || '-' }}</td>
            <td>{{ candidate.score }}</td>
            <td><StatusBadge :status="candidate.review_status" /></td>
            <td>
              <button class="secondary-button" type="button" @click="opportunities.reviewCandidate(candidate.id, 'accepted')">通过</button>
            </td>
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
import { useOpportunitiesStore } from '../stores/opportunities'

const opportunities = useOpportunitiesStore()
const fallback = [
  { id: 1, title: '昆山 AI 云平台采购意向', organization_name: '昆山某单位', score: 92, review_status: 'pending' }
]
const displayedQueue = computed(() => (opportunities.reviewQueue.length ? opportunities.reviewQueue : fallback))
</script>

