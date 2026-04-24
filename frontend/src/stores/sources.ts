import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type SourceItem = {
  id: number
  name: string
  home_url?: string
  priority?: string
  adapter_mode?: string
  login_mode?: string
  login_status?: string
  health_status?: string
  last_success_at?: string | null
  last_failure_reason?: string | null
}

export type SourceDetail = {
  source: SourceItem
  basic_rules: Record<string, unknown> | null
  active_rule: Record<string, unknown> | null
}

export type AdvancedRuleVersion = {
  id?: number
  version: number
  status: string
  selectors?: Record<string, unknown>
  [key: string]: unknown
}

export const useSourcesStore = defineStore('sources', {
  state: () => ({
    items: [] as SourceItem[],
    selectedDetail: null as SourceDetail | null,
    advancedRules: [] as AdvancedRuleVersion[],
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
      this.error = null
      try {
        const response = await client.get<{ items: SourceItem[] }>('/api/sources')
        this.items = response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载站点失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadSourceDetail(sourceId: number, client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        this.selectedDetail = await client.get<SourceDetail>(`/api/sources/${sourceId}`)
        return this.selectedDetail
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载站点详情失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadAdvancedRules(sourceId: number, client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: AdvancedRuleVersion[] }>(`/api/sources/${sourceId}/advanced-rules`)
        this.advancedRules = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载高级规则失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async updateBasicRules(sourceId: number, payload: Record<string, unknown>, client: Pick<ApiClient, 'patch'> = apiClient) {
      this.lastRuleUpdate = await client.patch<Record<string, unknown>>(`/api/sources/${sourceId}/basic-rules`, payload)
    },
    async createAdvancedRule(sourceId: number, payload: Record<string, unknown>, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        return await client.post<AdvancedRuleVersion>(`/api/sources/${sourceId}/advanced-rules`, payload)
      } catch (error) {
        this.error = error instanceof Error ? error.message : '创建高级规则失败'
        throw error
      }
    },
    async trialRunAdvancedRule(
      sourceId: number,
      version: number,
      maxItems = 5,
      client: Pick<ApiClient, 'post'> = apiClient
    ) {
      this.error = null
      try {
        return await client.post<Record<string, unknown>>(`/api/sources/${sourceId}/advanced-rules/${version}/trial-run`, {
          max_items: maxItems
        })
      } catch (error) {
        this.error = error instanceof Error ? error.message : '试运行高级规则失败'
        throw error
      }
    },
    async activateAdvancedRule(sourceId: number, version: number, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        const result = await client.post<AdvancedRuleVersion>(`/api/sources/${sourceId}/advanced-rules/${version}/activate`)
        await this.loadSourceDetail(sourceId)
        await this.loadAdvancedRules(sourceId)
        return result
      } catch (error) {
        this.error = error instanceof Error ? error.message : '启用高级规则失败'
        throw error
      }
    },
    async rollbackAdvancedRule(sourceId: number, version: number, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        const result = await client.post<AdvancedRuleVersion>(`/api/sources/${sourceId}/advanced-rules/${version}/rollback`)
        await this.loadSourceDetail(sourceId)
        await this.loadAdvancedRules(sourceId)
        return result
      } catch (error) {
        this.error = error instanceof Error ? error.message : '回滚高级规则失败'
        throw error
      }
    }
  }
})
