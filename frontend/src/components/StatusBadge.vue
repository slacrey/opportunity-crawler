<template>
  <span class="status-badge" :class="toneClass">{{ displayLabel }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status?: string | null
  label?: string
}>()

const displayLabel = computed(() => props.label ?? props.status ?? 'unknown')
const toneClass = computed(() => {
  if (['healthy', 'connected', 'succeeded', 'accepted', 'logged_in'].includes(props.status ?? '')) return 'status-success'
  if (['pending_login', 'login_required', 'operator_intervention_required', 'running'].includes(props.status ?? '')) {
    return 'status-warning'
  }
  if (['failed', 'rejected', 'disconnected'].includes(props.status ?? '')) return 'status-danger'
  return 'status-neutral'
})
</script>

