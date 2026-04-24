<template>
  <section class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">客户历史</h1>
        <p class="page-subtitle">已接受商机、活动和报价记录</p>
      </div>
      <button class="primary-button" type="button" :disabled="customers.loading" @click="refresh">刷新客户</button>
    </div>
    <p v-if="customers.error" class="state-message state-error">{{ customers.error }}</p>
    <DataTableShell title="客户列表">
      <table class="data-table">
        <thead>
          <tr><th>客户</th><th>地区</th><th>行业</th><th>商机</th><th>最近活动</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="customer in customers.items"
            :key="customer.id"
            :data-test="`customer-row-${customer.id}`"
            :class="{ 'selected-row': selectedCustomerName === customer.name }"
            @click="selectCustomer(customer.name)"
          >
            <td>{{ customer.name }}</td>
            <td>{{ customer.region || '-' }}</td>
            <td>{{ customer.industry || '-' }}</td>
            <td>{{ customer.opportunity_count ?? 0 }}</td>
            <td>{{ customer.last_activity_at || '-' }}</td>
          </tr>
          <tr v-if="customers.items.length === 0">
            <td colspan="5">{{ customers.loading ? '加载中...' : '暂无客户' }}</td>
          </tr>
        </tbody>
      </table>
    </DataTableShell>
    <section class="panel customer-history">
      <template v-if="history">
        <div class="history-header">
          <div>
            <h2 class="page-title">{{ history.customer?.name || selectedCustomerName }}</h2>
            <p class="page-subtitle">
              {{ history.customer?.region || '未知地区' }} · {{ history.customer?.industry || '未知行业' }}
            </p>
          </div>
          <strong>{{ history.opportunity_count ?? history.opportunities?.length ?? 0 }} 个商机</strong>
        </div>
        <div class="history-grid">
          <section class="history-block">
            <h3>商机</h3>
            <ul class="history-list">
              <li v-for="opportunity in history.opportunities ?? []" :key="opportunity.id">
                <strong>{{ opportunity.title || `#${opportunity.id}` }}</strong>
                <span>{{ opportunity.review_status || '-' }} · {{ opportunity.follow_up_status || '-' }}</span>
              </li>
              <li v-if="(history.opportunities ?? []).length === 0">暂无商机记录</li>
            </ul>
          </section>
          <section class="history-block">
            <h3>活动</h3>
            <ul class="history-list">
              <li v-for="activity in history.activities ?? []" :key="activity.id">
                <strong>{{ activity.activity_type || activity.type || '-' }}</strong>
                <span>{{ activity.content || activity.note || activity.occurred_at || '-' }}</span>
              </li>
              <li v-if="(history.activities ?? []).length === 0">暂无活动记录</li>
            </ul>
          </section>
          <section class="history-block">
            <h3>报价</h3>
            <ul class="history-list">
              <li v-for="quote in history.quotes ?? []" :key="quote.id">
                <strong>{{ quote.status || '-' }}</strong>
                <span>{{ quote.amount ?? quote.created_at ?? '-' }}</span>
              </li>
              <li v-if="(history.quotes ?? []).length === 0">暂无报价记录</li>
            </ul>
          </section>
        </div>
      </template>
      <template v-else>
        <h2 class="page-title">客户详情</h2>
        <p class="page-subtitle">选择一个客户后查看历史商机和跟进活动</p>
      </template>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import DataTableShell from '../components/DataTableShell.vue'
import { useCustomersStore } from '../stores/customers'

type HistoryOpportunity = {
  id: number | string
  title?: string
  review_status?: string
  follow_up_status?: string
}

type HistoryActivity = {
  id: number | string
  activity_type?: string
  type?: string
  content?: string
  note?: string
  occurred_at?: string
}

type HistoryQuote = {
  id: number | string
  status?: string
  amount?: number
  created_at?: string
}

type CustomerHistory = {
  customer?: {
    name?: string
    region?: string | null
    industry?: string | null
  }
  opportunity_count?: number
  opportunities?: HistoryOpportunity[]
  activities?: HistoryActivity[]
  quotes?: HistoryQuote[]
}

const customers = useCustomersStore()
const selectedCustomerName = ref('')
const history = computed(() => customers.selectedHistory as CustomerHistory | null)

onMounted(() => {
  void refresh()
})

async function refresh() {
  await customers.loadCustomers()
}

async function selectCustomer(customerName: string) {
  selectedCustomerName.value = customerName
  await customers.loadHistory(customerName)
}
</script>

<style scoped>
.customer-history {
  margin-top: 16px;
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.history-block h3 {
  margin: 0 0 8px;
  font-size: 14px;
}

.history-list {
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
  color: #526071;
  font-size: 13px;
}

.history-list li {
  display: grid;
  gap: 3px;
}

.history-list strong {
  color: #172033;
}

.selected-row {
  background: #f0f6ff;
}
</style>
