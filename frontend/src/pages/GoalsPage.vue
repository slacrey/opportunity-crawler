<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">目标进度</h1>
        <p class="page-subtitle">周拜访、报价和有效商机</p>
      </div>
    </div>
    <form class="goal-toolbar" data-test="goals-form" @submit.prevent="loadProgress">
      <label class="field-label">
        周起始日期
        <input v-model="weekStart" class="field-input" data-test="week-start" type="date" />
      </label>
      <button class="primary-button" type="submit" :disabled="goals.loading">刷新进度</button>
    </form>
    <p v-if="goals.error" class="state-message state-error">{{ goals.error }}</p>
    <div class="metric-grid">
      <article class="metric-card"><div class="metric-label">拜访</div><div class="metric-value">{{ progress.visits }}</div></article>
      <article class="metric-card"><div class="metric-label">报价</div><div class="metric-value">{{ progress.quotes }}</div></article>
      <article class="metric-card">
        <div class="metric-label">有效商机</div>
        <div class="metric-value">{{ progress.accepted_opportunities }}</div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useGoalsStore, type WeeklyProgress } from '../stores/goals'

const goals = useGoalsStore()
const weekStart = ref(defaultWeekStart())
const progress = computed<WeeklyProgress>(
  () => goals.weeklyProgress ?? { week_start: weekStart.value, visits: 0, quotes: 0, accepted_opportunities: 0 }
)

onMounted(() => {
  void loadProgress()
})

async function loadProgress() {
  await goals.loadWeeklyProgress(weekStart.value)
}

function defaultWeekStart() {
  const date = new Date()
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  return toDateInputValue(date)
}

function toDateInputValue(date: Date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return localDate.toISOString().slice(0, 10)
}
</script>

<style scoped>
.goal-toolbar {
  display: flex;
  align-items: end;
  gap: 12px;
  margin-bottom: 16px;
}

.goal-toolbar .field-label {
  width: min(240px, 100%);
}

@media (max-width: 640px) {
  .goal-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
