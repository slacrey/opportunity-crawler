<template>
  <section class="panel">
    <div class="page-header">
      <div>
        <h2 class="page-title">采集规则</h2>
        <p class="page-subtitle">{{ sourceName }}</p>
      </div>
    </div>
    <form class="form-grid" @submit.prevent="$emit('save', form)">
      <label class="field-label">
        地区
        <input v-model="form.regions" class="field-input" />
      </label>
      <label class="field-label">
        关键词
        <input v-model="form.demand_keywords" class="field-input" />
      </label>
      <label class="field-label">
        频率
        <select v-model="form.frequency" class="field-input">
          <option value="daily">daily</option>
          <option value="weekly">weekly</option>
          <option value="manual">manual</option>
        </select>
      </label>
      <button class="primary-button" type="submit">保存</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

defineProps<{ sourceName: string }>()
defineEmits<{ save: [payload: Record<string, string>] }>()

const form = reactive({
  regions: '昆山,太仓',
  demand_keywords: 'AI,云平台',
  frequency: 'daily'
})
</script>

