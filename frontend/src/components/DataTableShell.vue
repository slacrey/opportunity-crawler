<template>
  <section class="table-shell">
    <div class="table-toolbar">
      <strong>{{ title }}</strong>
      <slot name="actions" />
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string }>()
</script>

