import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type AuditLog = {
  id: number
  action: string
  resource_type?: string
  resource_id?: string
  actor_username?: string | null
  created_at?: string
  after?: Record<string, unknown> | null
}

export const useAuditStore = defineStore('audit', {
  state: () => ({
    items: [] as AuditLog[],
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadLogs(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: AuditLog[] }>('/api/audit-logs')
        this.items = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载审计日志失败'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
