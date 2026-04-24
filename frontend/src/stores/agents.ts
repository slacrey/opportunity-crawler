import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type AgentInstance = {
  agent_id: string
  host_id?: string
  hostname?: string
  status: string
  capacity?: number
  active_sessions?: number
  last_heartbeat_at?: string | null
}

export const useAgentsStore = defineStore('agents', {
  state: () => ({
    items: [] as AgentInstance[],
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadAgents(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: AgentInstance[] }>('/api/agents')
        this.items = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载 Agent 失败'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
