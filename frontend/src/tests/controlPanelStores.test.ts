import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAgentsStore } from '../stores/agents'
import { useAuditStore } from '../stores/audit'
import { useCustomersStore } from '../stores/customers'
import { useDashboardStore } from '../stores/dashboard'
import { useGoalsStore } from '../stores/goals'
import { useNotificationsStore } from '../stores/notifications'
import { useOpportunitiesStore } from '../stores/opportunities'
import { useRuntimeStore } from '../stores/runtime'
import { useSourcesStore } from '../stores/sources'

describe('control panel stores', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('loads dashboard summary and clears stale errors on retry', async () => {
    const dashboard = useDashboardStore()

    await expect(
      dashboard.loadSummary({
        get: async () => {
          throw new Error('network down')
        }
      })
    ).rejects.toThrow('network down')
    expect(dashboard.error).toBe('network down')

    await dashboard.loadSummary({
      get: async (path: string) => {
        expect(path).toBe('/api/dashboard/summary')
        return {
          sources: { total: 3, healthy: 1, failed: 1, login_required: 1 },
          opportunities: { pending: 2, accepted: 1, high_score: 2 },
          runs: { running: 1, failed: 1 },
          agents: { online: 1 }
        }
      }
    })

    expect(dashboard.error).toBeNull()
    expect(dashboard.summary?.opportunities.pending).toBe(2)
  })

  it('loads and mutates opportunities through backend APIs', async () => {
    const opportunities = useOpportunitiesStore()

    await opportunities.loadReviewQueue({
      get: async (path: string) => {
        expect(path).toBe('/api/opportunities?review_status=pending')
        return { items: [{ id: 1, title: '昆山项目', score: 90, review_status: 'pending' }] }
      }
    })
    await opportunities.loadDetail(1, {
      get: async (path: string) => {
        expect(path).toBe('/api/opportunities/1')
        return {
          candidate: { id: 1, title: '昆山项目', score: 90, review_status: 'pending' },
          evidence: { raw_text: '原文' },
          analysis: { extracted_facts: {} }
        }
      }
    })
    const created = await opportunities.createManualImport(
      { source_id: 2, title: '新项目', body: '正文' },
      {
        post: async (path: string, payload: unknown) => {
          expect(path).toBe('/api/opportunities/manual-import')
          expect(payload).toMatchObject({ title: '新项目' })
          return { id: 2, title: '新项目', score: 70, review_status: 'pending' }
        }
      }
    )
    await opportunities.updateFollowUp(1, 'visited', '已拜访', {
      post: async (path: string, payload: unknown) => {
        expect(path).toBe('/api/opportunities/1/follow-up')
        expect(payload).toEqual({ follow_up_status: 'visited', note: '已拜访' })
        return { id: 1, title: '昆山项目', score: 90, review_status: 'pending', follow_up_status: 'visited' }
      }
    })

    expect(opportunities.reviewQueue).toHaveLength(2)
    expect(created.id).toBe(2)
    expect(opportunities.selected?.follow_up_status).toBe('visited')
  })

  it('loads source detail and advanced rule versions', async () => {
    const sources = useSourcesStore()

    await sources.loadSourceDetail(1, {
      get: async (path: string) => {
        expect(path).toBe('/api/sources/1')
        return {
          source: { id: 1, name: '中国政府采购网', health_status: 'healthy' },
          basic_rules: { frequency: 'daily' },
          active_rule: { version: 2, status: 'active' }
        }
      }
    })
    await sources.loadAdvancedRules(1, {
      get: async (path: string) => {
        expect(path).toBe('/api/sources/1/advanced-rules')
        return { items: [{ version: 2, status: 'active', selectors: { list_selector: '.item' } }] }
      }
    })

    expect(sources.selectedDetail?.source.name).toBe('中国政府采购网')
    expect(sources.advancedRules[0].version).toBe(2)
  })

  it('loads runtime runs and health state', async () => {
    const runtime = useRuntimeStore()

    await runtime.loadRuns({
      get: async (path: string) => {
        expect(path).toBe('/api/collection-runs')
        return { items: [{ run_id: 'run-1', source_id: 1, status: 'failed', item_count: 3 }] }
      }
    })
    await runtime.loadHealth({
      get: async (path: string) => {
        expect(path).toBe('/api/health')
        return { database: { ok: true }, agents: { online: 0 } }
      }
    })

    expect(runtime.runs['run-1'].status).toBe('failed')
    expect(runtime.health?.database.ok).toBe(true)
  })

  it('loads operational list stores from their backend endpoints', async () => {
    const agents = useAgentsStore()
    const notifications = useNotificationsStore()
    const audit = useAuditStore()
    const customers = useCustomersStore()
    const goals = useGoalsStore()

    await agents.loadAgents({ get: async () => ({ items: [{ agent_id: 'local-agent', status: 'online' }] }) })
    await notifications.loadLogs({ get: async () => ({ items: [{ id: 1, status: 'failed' }] }) })
    await audit.loadLogs({ get: async () => ({ items: [{ id: 1, action: 'opportunity.review' }] }) })
    await customers.loadCustomers({ get: async () => ({ items: [{ id: 1, name: '昆山某单位' }] }) })
    await goals.loadWeeklyProgress('2026-04-20', {
      get: async (path: string) => {
        expect(path).toBe('/api/goals/weekly-progress?week_start=2026-04-20')
        return { week_start: '2026-04-20', accepted_opportunities: 1, visits: 1, quotes: 0 }
      }
    })

    expect(agents.items[0].agent_id).toBe('local-agent')
    expect(notifications.items[0].status).toBe('failed')
    expect(audit.items[0].action).toBe('opportunity.review')
    expect(customers.items[0].name).toBe('昆山某单位')
    expect(goals.weeklyProgress?.visits).toBe(1)
  })
})
