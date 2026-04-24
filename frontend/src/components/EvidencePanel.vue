<template>
  <section class="panel">
    <h2 class="page-title">证据</h2>
    <p class="page-subtitle">{{ url || '无来源链接' }}</p>
    <pre>{{ rawText }}</pre>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  url?: string | null
  rawText?: string | null
}>()
</script>
