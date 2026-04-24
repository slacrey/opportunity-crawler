<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">站点管理</h1>
        <p class="page-subtitle">两层规则、登录状态和采集健康</p>
      </div>
      <div class="action-row page-actions">
        <button class="secondary-button" type="button" :disabled="sources.loading" @click="refreshSources">刷新站点</button>
        <button
          class="primary-button"
          type="button"
          data-test="start-collection"
          :disabled="!canStartCollection || collectionBusy"
          @click="startCollection"
        >
          启动采集
        </button>
      </div>
    </div>
    <p v-if="sources.error || runtime.error" class="state-message state-error">{{ sources.error || runtime.error }}</p>
    <p v-if="operationMessage" class="state-message state-info">{{ operationMessage }}</p>
    <DataTableShell title="采集站点">
      <table class="data-table">
        <thead>
          <tr><th>站点</th><th>模式</th><th>登录</th><th>健康</th><th>最近结果</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="source in sources.items"
            :key="source.id"
            :data-test="`source-row-${source.id}`"
            :class="{ 'selected-row': selectedSourceId === source.id }"
            @click="selectSource(source.id)"
          >
            <td>{{ source.name }}</td>
            <td>{{ source.adapter_mode }}</td>
            <td><StatusBadge :status="source.login_status" /></td>
            <td><StatusBadge :status="source.health_status" /></td>
            <td>{{ source.last_failure_reason || source.last_success_at || '-' }}</td>
          </tr>
          <tr v-if="sources.items.length === 0">
            <td colspan="5">{{ sources.loading ? '加载中...' : '暂无站点' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
    <div class="metric-grid source-edit-grid">
      <SourceRuleDrawer
        v-if="sources.selectedDetail"
        :source-name="sources.selectedDetail.source.name"
        :model-value="sources.selectedDetail.basic_rules"
        :disabled="!canUpdateBasicRules || ruleBusy"
        @save="saveBasicRules"
      />
      <section v-else class="panel">
        <h2 class="page-title">采集规则</h2>
        <p class="page-subtitle">选择一个站点后编辑规则</p>
      </section>
      <section class="panel">
        <h2 class="page-title">高级适配规则</h2>
        <p v-if="ruleMessage" class="page-subtitle">{{ ruleMessage }}</p>
        <AdvancedRuleEditor
          :model-value="advancedRule"
          :disabled="!canUpdateAdvancedRules || ruleBusy"
          @preview="previewAdvancedRule"
          @activate="activateAdvancedRule"
        />
        <p v-if="!canUpdateAdvancedRules" class="page-subtitle">当前账号没有高级规则变更权限</p>
        <div class="rule-version-list">
          <strong>版本</strong>
          <button
            v-for="rule in sources.advancedRules"
            :key="rule.version"
            class="secondary-button"
            type="button"
            :disabled="!canUpdateAdvancedRules || ruleBusy"
            @click="rollbackRule(rule.version)"
          >
            version {{ rule.version }} · {{ rule.status }}
          </button>
          <span v-if="sources.advancedRules.length === 0" class="page-subtitle">暂无高级规则版本</span>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AdvancedRuleEditor from '../components/AdvancedRuleEditor.vue'
import DataTableShell from '../components/DataTableShell.vue'
import SourceRuleDrawer from '../components/SourceRuleDrawer.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'
import { useRuntimeStore } from '../stores/runtime'
import { useSourcesStore } from '../stores/sources'

const auth = useAuthStore()
const runtime = useRuntimeStore()
const sources = useSourcesStore()
const selectedSourceId = ref<number | null>(null)
const ruleMessage = ref('')
const ruleBusy = ref(false)
const collectionBusy = ref(false)
const operationMessage = ref('')
const canUpdateBasicRules = computed(() => auth.can('source.basic_rules:update'))
const canUpdateAdvancedRules = computed(() => auth.can('source.advanced_rules:update'))
const canStartCollection = computed(() => selectedSourceId.value !== null && auth.can('collection_runs:manage'))
const advancedRule = computed(() => {
  const active = sources.selectedDetail?.active_rule
  if (active) return active as Record<string, unknown>
  return {
    adapter_mode: sources.selectedDetail?.source.adapter_mode ?? 'manual_import',
    entry_url: sources.selectedDetail?.source.home_url ?? 'manual://import',
    login_mode: sources.selectedDetail?.source.login_mode ?? 'not_required'
  }
})

onMounted(async () => {
  await refreshSources()
})

async function refreshSources() {
  await sources.loadSources()
}

async function selectSource(sourceId: number) {
  selectedSourceId.value = sourceId
  ruleMessage.value = ''
  operationMessage.value = ''
  await Promise.all([sources.loadSourceDetail(sourceId), sources.loadAdvancedRules(sourceId)])
}

async function startCollection() {
  if (selectedSourceId.value === null || !canStartCollection.value || collectionBusy.value) return
  collectionBusy.value = true
  operationMessage.value = ''
  try {
    const result = await runtime.startCollectionRun(selectedSourceId.value)
    operationMessage.value = `采集已启动：${result.run.run_id}`
  } finally {
    collectionBusy.value = false
  }
}

async function saveBasicRules(payload: Record<string, unknown>) {
  if (selectedSourceId.value === null || !canUpdateBasicRules.value || ruleBusy.value) return
  ruleBusy.value = true
  try {
    await sources.updateBasicRules(selectedSourceId.value, payload)
    await sources.loadSourceDetail(selectedSourceId.value)
    ruleMessage.value = '基础规则已保存'
  } finally {
    ruleBusy.value = false
  }
}

async function previewAdvancedRule(payload: Record<string, unknown>) {
  if (selectedSourceId.value === null || !canUpdateAdvancedRules.value || ruleBusy.value) return
  ruleBusy.value = true
  try {
    const created = await sources.createAdvancedRule(selectedSourceId.value, payload)
    const preview = await sources.trialRunAdvancedRule(selectedSourceId.value, created.version)
    await sources.loadAdvancedRules(selectedSourceId.value)
    ruleMessage.value = `试运行完成，预览 ${Array.isArray(preview.preview_rows) ? preview.preview_rows.length : 0} 条`
  } finally {
    ruleBusy.value = false
  }
}

async function activateAdvancedRule(payload: Record<string, unknown>) {
  if (selectedSourceId.value === null || !canUpdateAdvancedRules.value || ruleBusy.value) return
  ruleBusy.value = true
  try {
    const created = await sources.createAdvancedRule(selectedSourceId.value, payload)
    await sources.activateAdvancedRule(selectedSourceId.value, created.version)
    ruleMessage.value = `version ${created.version} 已启用`
  } finally {
    ruleBusy.value = false
  }
}

async function rollbackRule(version: number) {
  if (selectedSourceId.value === null || !canUpdateAdvancedRules.value || ruleBusy.value) return
  ruleBusy.value = true
  try {
    await sources.rollbackAdvancedRule(selectedSourceId.value, version)
    ruleMessage.value = `已回滚到 version ${version}`
  } finally {
    ruleBusy.value = false
  }
}
</script>

<style scoped>
.source-edit-grid {
  margin-top: 16px;
  align-items: start;
}

.page-actions {
  justify-content: flex-end;
}

.selected-row {
  background: #f0f6ff;
}

.rule-version-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
</style>
