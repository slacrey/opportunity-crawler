<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">商机复核</h1>
        <p class="page-subtitle">高分候选、证据和跟进状态</p>
      </div>
      <button class="primary-button" type="button" :disabled="opportunities.loading" @click="opportunities.loadReviewQueue()">
        刷新队列
      </button>
    </div>
    <p v-if="opportunities.error" class="state-message state-error">{{ opportunities.error }}</p>
    <section class="panel import-panel">
      <h2 class="section-title">手动导入</h2>
      <p v-if="!canWriteOpportunities" class="page-subtitle">当前账号没有手动导入权限</p>
      <form class="form-grid import-grid" data-test="manual-import" @submit.prevent="submitManualImport">
        <label class="field-label">
          来源 ID
          <input v-model.number="manualForm.source_id" class="field-input" type="number" min="1" />
        </label>
        <label class="field-label">
          标题
          <input v-model="manualForm.title" data-test="manual-title" class="field-input" required />
        </label>
        <label class="field-label wide-field">
          正文
          <textarea v-model="manualForm.body" data-test="manual-body" class="field-input" required />
        </label>
        <label class="field-label">
          客户
          <input v-model="manualForm.organization_name" class="field-input" />
        </label>
        <label class="field-label">
          地区
          <input v-model="manualForm.region" class="field-input" />
        </label>
        <button class="primary-button" type="submit" data-test="manual-submit" :disabled="manualSubmitDisabled">导入</button>
      </form>
    </section>
    <DataTableShell title="待复核商机">
      <table class="data-table">
        <thead>
          <tr><th>标题</th><th>客户</th><th>评分</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="candidate in opportunities.reviewQueue" :key="candidate.id">
            <td>{{ candidate.title }}</td>
            <td>{{ candidate.organization_name || '-' }}</td>
            <td>{{ candidate.score }}</td>
            <td><StatusBadge :status="candidate.review_status" /></td>
            <td>
              <div class="action-row">
                <button
                  class="secondary-button"
                  type="button"
                  :data-test="`accept-${candidate.id}`"
                  :disabled="!canReviewOpportunities || reviewingId === candidate.id"
                  @click="reviewCandidate(candidate.id, 'accepted')"
                >
                  通过
                </button>
                <button
                  class="secondary-button"
                  type="button"
                  :disabled="!canReviewOpportunities || reviewingId === candidate.id"
                  @click="reviewCandidate(candidate.id, 'rejected')"
                >
                  拒绝
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="opportunities.reviewQueue.length === 0">
            <td colspan="5">{{ opportunities.loading ? '加载中...' : '暂无待复核商机' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'
import { useOpportunitiesStore } from '../stores/opportunities'

const auth = useAuthStore()
const opportunities = useOpportunitiesStore()
const manualForm = reactive({
  source_id: 1,
  title: '',
  body: '',
  organization_name: '',
  region: ''
})
const manualSubmitting = ref(false)
const reviewingId = ref<number | null>(null)
const canWriteOpportunities = computed(() => auth.can('opportunities:write'))
const canReviewOpportunities = computed(() => auth.can('opportunities:review'))
const manualSubmitDisabled = computed(() => opportunities.loading || manualSubmitting.value || !canWriteOpportunities.value)

onMounted(() => {
  void opportunities.loadReviewQueue()
})

async function submitManualImport() {
  if (manualSubmitDisabled.value) return
  manualSubmitting.value = true
  try {
    await opportunities.createManualImport({
      source_id: manualForm.source_id,
      title: manualForm.title,
      body: manualForm.body,
      organization_name: manualForm.organization_name || null,
      region: manualForm.region || null
    })
    manualForm.title = ''
    manualForm.body = ''
  } finally {
    manualSubmitting.value = false
  }
}

async function reviewCandidate(candidateId: number, status: 'accepted' | 'rejected') {
  if (!canReviewOpportunities.value || reviewingId.value !== null) return
  reviewingId.value = candidateId
  try {
    await opportunities.reviewCandidate(candidateId, status)
  } finally {
    reviewingId.value = null
  }
}
</script>

<style scoped>
.import-panel {
  margin-bottom: 16px;
}

.import-grid {
  grid-template-columns: minmax(80px, 120px) minmax(220px, 1fr) minmax(180px, 220px) minmax(120px, 160px) auto;
  align-items: end;
}

.wide-field {
  grid-column: span 2;
}
</style>
