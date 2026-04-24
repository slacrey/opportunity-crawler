import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type SourceItem = {
  id: number
  name: string
  priority?: string
  adapter_mode?: string
  login_mode?: string
  login_status?: string
  health_status?: string
  last_success_at?: string | null
  last_failure_reason?: string | null
}

export const useSourcesStore = defineStore('sources', {
  state: () => ({
    items: [] as SourceItem[],
    loading: false,
    error: null as string | null,
    lastRuleUpdate: null as Record<string, unknown> | null
  }),
  getters: {
    healthSummary(state) {
      return state.items.reduce(
        (summary, source) => {
          if (source.health_status === 'healthy') summary.healthy += 1
          if (source.health_status === 'failed') summary.failed += 1
          if (source.login_status && source.login_status !== 'not_required' && source.login_status !== 'logged_in') {
            summary.loginRequired += 1
          }
          return summary
        },
        { healthy: 0, failed: 0, loginRequired: 0 }
      )
    }
  },
  actions: {
    async loadSources(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      try {
        const response = await client.get<{ items: SourceItem[] }>('/api/sources')
        this.items = response.items
      } finally {
        this.loading = false
      }
    },
    async updateBasicRules(sourceId: number, payload: Record<string, unknown>, client: Pick<ApiClient, 'patch'> = apiClient) {
      this.lastRuleUpdate = await client.patch<Record<string, unknown>>(`/api/sources/${sourceId}/basic-rules`, payload)
    }
  }
})

