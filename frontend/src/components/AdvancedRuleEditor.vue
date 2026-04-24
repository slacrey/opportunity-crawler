<template>
  <section class="drawer-surface">
    <label class="field-label">
      高级规则 JSON
      <textarea v-model="draft" class="field-input code-editor" />
    </label>
    <p v-if="error" class="page-subtitle">{{ error }}</p>
    <div>
      <button class="primary-button" type="button" data-test="preview" :disabled="disabled" @click="emitPreview">预览</button>
      <button class="secondary-button" type="button" data-test="activate" :disabled="disabled" @click="emitActivate">启用</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ modelValue: Record<string, unknown>; disabled?: boolean }>()
const emit = defineEmits<{
  preview: [payload: Record<string, unknown>]
  activate: [payload: Record<string, unknown>]
}>()

const draft = ref(JSON.stringify(props.modelValue, null, 2))
const error = ref('')

watch(
  () => props.modelValue,
  (value) => {
    draft.value = JSON.stringify(value, null, 2)
  }
)

function parseDraft() {
  try {
    error.value = ''
    return JSON.parse(draft.value) as Record<string, unknown>
  } catch {
    error.value = '规则 JSON 格式无效'
    return null
  }
}

function emitPreview() {
  if (props.disabled) return
  const payload = parseDraft()
  if (payload) emit('preview', payload)
}

function emitActivate() {
  if (props.disabled) return
  const payload = parseDraft()
  if (payload) emit('activate', payload)
}
</script>
