<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">商机详情</h1>
        <p class="page-subtitle">候选 ID: {{ route.params.id }}</p>
      </div>
      <StatusBadge status="accepted" />
    </div>
    <div class="metric-grid">
      <article class="metric-card">
        <div class="metric-label">评分</div>
        <div class="metric-value">92</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">优先级</div>
        <div class="metric-value">P0</div>
      </article>
    </div>
    <EvidencePanel url="https://example.test/project/1" raw-text="昆山 制造业 AI 云平台 数字化转型采购意向" />
  </section>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import EvidencePanel from '../components/EvidencePanel.vue'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
</script>

