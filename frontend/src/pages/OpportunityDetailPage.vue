<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ candidate?.title || '商机详情' }}</h1>
        <p class="page-subtitle">候选 ID: {{ route.params.id }}</p>
      </div>
      <StatusBadge :status="candidate?.review_status" />
    </div>
    <p v-if="opportunities.error" class="state-message state-error">{{ opportunities.error }}</p>
    <div class="metric-grid">
      <article class="metric-card">
        <div class="metric-label">评分</div>
        <div class="metric-value">{{ candidate?.score ?? 0 }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">优先级</div>
        <div class="metric-value">{{ candidate?.priority_label || '-' }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">来源</div>
        <div class="metric-value compact-value">{{ sourceName }}</div>
      </article>
      <article class="metric-card">
        <div class="metric-label">跟进</div>
        <div class="metric-value compact-value">{{ candidate?.follow_up_status || 'none' }}</div>
      </article>
    </div>
    <section class="panel detail-panel">
      <h2 class="section-title">复核与跟进</h2>
      <div class="action-row">
        <button class="secondary-button" type="button" :disabled="actionBusy || !canReview" @click="review('accepted')">通过</button>
        <button class="secondary-button" type="button" :disabled="actionBusy || !canReview" @click="review('rejected')">拒绝</button>
      </div>
      <form class="form-grid follow-up-grid" data-test="follow-up-form" @submit.prevent="submitFollowUp">
        <label class="field-label">
          跟进状态
          <select v-model="followUp.status" data-test="follow-up-status" class="field-input">
            <option value="none">none</option>
            <option value="contacted">contacted</option>
            <option value="visited">visited</option>
            <option value="quoted">quoted</option>
            <option value="won">won</option>
            <option value="lost">lost</option>
          </select>
        </label>
        <label class="field-label">
          备注
          <input v-model="followUp.note" data-test="follow-up-note" class="field-input" />
        </label>
        <button class="primary-button" type="submit" :disabled="actionBusy || !canReview">保存跟进</button>
      </form>
      <p v-if="!canReview" class="page-subtitle">当前账号没有复核和跟进权限</p>
    </section>
    <EvidencePanel :url="evidenceUrl" :raw-text="evidenceText" />
    <section class="panel detail-panel">
      <h2 class="section-title">评分原因</h2>
      <ul class="plain-list">
        <li v-for="reason in scoringReasons" :key="reason">{{ reason }}</li>
        <li v-if="scoringReasons.length === 0">暂无评分原因</li>
      </ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import EvidencePanel from '../components/EvidencePanel.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'
import { useOpportunitiesStore } from '../stores/opportunities'

const route = useRoute()
const auth = useAuthStore()
const opportunities = useOpportunitiesStore()
const candidateId = computed(() => Number(route.params.id))
const detail = computed(() => opportunities.selectedDetail)
const candidate = computed(() => detail.value?.candidate ?? null)
const evidence = computed(() => detail.value?.evidence ?? null)
const sourceName = computed(() => String(detail.value?.source?.name ?? '-'))
const evidenceUrl = computed(() => (typeof evidence.value?.url === 'string' ? evidence.value.url : undefined))
const evidenceText = computed(() => (typeof evidence.value?.raw_text === 'string' ? evidence.value.raw_text : undefined))
const scoringReasons = computed(() => {
  const value = detail.value?.analysis?.scoring_reasons
  return Array.isArray(value) ? value.map(String) : []
})
const followUp = reactive({
  status: 'none',
  note: ''
})
const actionBusy = ref(false)
const canReview = computed(() => auth.can('opportunities:review'))

watch(
  candidate,
  (value) => {
    followUp.status = value?.follow_up_status ?? 'none'
  },
  { immediate: true }
)

onMounted(() => {
  void opportunities.loadDetail(candidateId.value)
})

async function review(status: 'accepted' | 'rejected') {
  if (!canReview.value || actionBusy.value) return
  actionBusy.value = true
  try {
    await opportunities.reviewCandidate(candidateId.value, status)
  } finally {
    actionBusy.value = false
  }
}

async function submitFollowUp() {
  if (!canReview.value || actionBusy.value) return
  actionBusy.value = true
  try {
    await opportunities.updateFollowUp(candidateId.value, followUp.status, followUp.note || null)
  } finally {
    actionBusy.value = false
  }
}
</script>

<style scoped>
.detail-panel {
  margin-bottom: 16px;
}

.compact-value {
  font-size: 18px;
}

.follow-up-grid {
  grid-template-columns: minmax(160px, 220px) minmax(240px, 1fr) auto;
  align-items: end;
  margin-top: 12px;
}
</style>
