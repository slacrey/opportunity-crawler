<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">站点管理</h1>
        <p class="page-subtitle">两层规则、登录状态和采集健康</p>
      </div>
      <button class="primary-button" type="button" @click="sources.loadSources()">刷新站点</button>
    </div>
    <DataTableShell title="采集站点">
      <table class="data-table">
        <thead>
          <tr><th>站点</th><th>模式</th><th>登录</th><th>健康</th><th>最近结果</th></tr>
        </thead>
        <tbody>
          <tr v-for="source in displayedSources" :key="source.id">
            <td>{{ source.name }}</td>
            <td>{{ source.adapter_mode }}</td>
            <td><StatusBadge :status="source.login_status" /></td>
            <td><StatusBadge :status="source.health_status" /></td>
            <td>{{ source.last_failure_reason || source.last_success_at || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
    <div class="metric-grid source-edit-grid">
      <SourceRuleDrawer source-name="中国政府采购网" />
      <section class="panel">
        <h2 class="page-title">高级适配规则</h2>
        <AdvancedRuleEditor
          :model-value="advancedRule"
          @preview="previewRule = $event"
          @activate="previewRule = $event"
        />
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AdvancedRuleEditor from '../components/AdvancedRuleEditor.vue'
import DataTableShell from '../components/DataTableShell.vue'
import SourceRuleDrawer from '../components/SourceRuleDrawer.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useSourcesStore } from '../stores/sources'

const sources = useSourcesStore()
const fallbackSources = [
  {
    id: 1,
    name: '中国政府采购网',
    adapter_mode: 'public_search_list_detail',
    login_status: 'not_required',
    health_status: 'healthy',
    last_success_at: '2026-04-24 08:30'
  },
  {
    id: 2,
    name: '建设网',
    adapter_mode: 'login_search_list_detail',
    login_status: 'pending_login',
    health_status: 'unknown',
    last_failure_reason: '等待人工登录'
  }
]
const displayedSources = computed(() => (sources.items.length ? sources.items : fallbackSources))
const advancedRule = {
  adapter_mode: 'public_search_list_detail',
  entry_url: 'https://www.ccgp.gov.cn',
  login_mode: 'not_required',
  selectors: {
    list_selector: '.result',
    detail_link_selector: 'a',
    content_selector: '.content'
  }
}
const previewRule = ref<Record<string, unknown> | null>(null)
</script>

<style scoped>
.source-edit-grid {
  margin-top: 16px;
  align-items: start;
}
</style>

