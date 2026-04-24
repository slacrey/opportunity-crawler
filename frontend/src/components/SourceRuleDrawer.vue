<template>
  <section class="panel">
    <div class="page-header">
      <div>
        <h2 class="page-title">采集规则</h2>
        <p class="page-subtitle">{{ sourceName }}</p>
      </div>
    </div>
    <form class="form-grid" @submit.prevent="emitSave">
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
      <button class="primary-button" type="submit" data-test="basic-rules-save" :disabled="disabled">保存</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  sourceName: string
  modelValue?: Record<string, unknown> | null
  disabled?: boolean
}>()
const emit = defineEmits<{ save: [payload: Record<string, unknown>] }>()

const form = reactive({
  regions: '',
  demand_keywords: '',
  frequency: 'daily'
})

watch(
  () => props.modelValue,
  (value) => {
    form.regions = listToText(value?.regions)
    form.demand_keywords = listToText(value?.demand_keywords)
    form.frequency = typeof value?.frequency === 'string' ? value.frequency : 'daily'
  },
  { immediate: true }
)

function emitSave() {
  if (props.disabled) return
  emit('save', {
    regions: textToList(form.regions),
    demand_keywords: textToList(form.demand_keywords),
    frequency: form.frequency
  })
}

function listToText(value: unknown) {
  return Array.isArray(value) ? value.join(',') : ''
}

function textToList(value: string) {
  return value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}
</script>
