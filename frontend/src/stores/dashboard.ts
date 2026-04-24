import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type DashboardSummary = {
  sources: {
    total: number
    healthy: number
    failed: number
    login_required: number
  }
  opportunities: {
    pending: number
    accepted: number
    high_score: number
  }
  runs: {
    running: number
    failed: number
  }
  agents: {
    online: number
  }
}

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    summary: null as DashboardSummary | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadSummary(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        this.summary = await client.get<DashboardSummary>('/api/dashboard/summary')
        return this.summary
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载仪表盘失败'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
