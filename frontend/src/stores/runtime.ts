import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'
import type { RuntimeEvent } from '../api/events'

export type RunState = {
  run_id: string
  source_id?: number
  source_name?: string
  status: string
  item_count?: number
  failure_kind?: string | null
  diagnostic_snapshot?: Record<string, unknown> | null
  scheduled_at?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export const useRuntimeStore = defineStore('runtime', {
  state: () => ({
    eventState: 'connected' as 'connected' | 'disconnected',
    runs: {} as Record<string, RunState>,
    health: null as Record<string, any> | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadRuns(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: RunState[] }>('/api/collection-runs')
        this.runs = response.items.reduce<Record<string, RunState>>((runs, run) => {
          runs[run.run_id] = run
          return runs
        }, {})
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载采集运行失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadHealth(client: Pick<ApiClient, 'get'> = apiClient) {
      this.error = null
      try {
        this.health = await client.get<Record<string, any>>('/api/health')
        return this.health
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载运行状态失败'
        throw error
      }
    },
    async startCollectionRun(sourceId: number, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        const response = await client.post<{ run: RunState }>(`/api/sources/${sourceId}/collection-runs`)
        this.runs[response.run.run_id] = response.run
        return response
      } catch (error) {
        this.error = error instanceof Error ? error.message : '启动采集失败'
        throw error
      }
    },
    applyEvent(event: RuntimeEvent) {
      if (!event.run_id) return
      const status = event.type.replace(/^run_/, '')
      this.runs[event.run_id] = {
        ...this.runs[event.run_id],
        run_id: event.run_id,
        source_id: event.source_id,
        status,
        item_count: event.item_count ?? this.runs[event.run_id]?.item_count
      }
    }
  }
})
