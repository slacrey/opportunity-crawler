import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type NotificationLog = {
  id: number
  channel?: string
  template?: string
  status: string
  failure_reason?: string | null
  candidate_ids?: number[]
  created_at?: string
}

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    items: [] as NotificationLog[],
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadLogs(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: NotificationLog[] }>('/api/notifications/logs')
        this.items = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载通知日志失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async sendDigest(simulateFailure = false, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        return await client.post<Record<string, unknown>>('/api/notifications/dingtalk/digest', {
          simulate_failure: simulateFailure
        })
      } catch (error) {
        this.error = error instanceof Error ? error.message : '发送摘要失败'
        throw error
      }
    }
  }
})
