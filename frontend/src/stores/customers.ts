import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type Customer = {
  id: number
  name: string
  region?: string | null
  industry?: string | null
  opportunity_count?: number
  last_activity_at?: string | null
}

export const useCustomersStore = defineStore('customers', {
  state: () => ({
    items: [] as Customer[],
    selectedHistory: null as Record<string, unknown> | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadCustomers(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: Customer[] }>('/api/customers')
        this.items = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载客户失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadHistory(customerName: string, client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        this.selectedHistory = await client.get<Record<string, unknown>>(
          `/api/customers/${encodeURIComponent(customerName)}/history`
        )
        return this.selectedHistory
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载客户历史失败'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
