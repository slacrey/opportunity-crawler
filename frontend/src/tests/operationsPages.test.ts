import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AgentsPage from '../pages/AgentsPage.vue'
import AuditLogsPage from '../pages/AuditLogsPage.vue'
import CollectionRunsPage from '../pages/CollectionRunsPage.vue'
import CustomersPage from '../pages/CustomersPage.vue'
import GoalsPage from '../pages/GoalsPage.vue'
import NotificationsPage from '../pages/NotificationsPage.vue'
import { useAuthStore } from '../stores/auth'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn()
}))

vi.mock('../api/client', () => ({
  apiClient: apiMock,
  API_PATH_PREFIX: '/api/'
}))

describe('operations control panel pages', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'admin', roles: ['administrator'] }
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.patch.mockReset()
  })

  it('collection runs page renders backend runs with failure diagnostics', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/collection-runs') {
        return {
          items: [
            {
              run_id: 'run-ops',
              source_name: '江苏省采购网',
              status: 'failed',
              item_count: 5,
              failure_kind: 'parse_error',
              diagnostic_snapshot: { selector: '.notice-item', stage: 'detail' }
            }
          ]
        }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(CollectionRunsPage)
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/collection-runs')
    expect(wrapper.text()).toContain('run-ops')
    expect(wrapper.text()).toContain('江苏省采购网')
    expect(wrapper.text()).toContain('parse_error')
    expect(wrapper.text()).toContain('.notice-item')
    expect(wrapper.text()).not.toContain('run-demo')
  })

  it('customers page loads customers and opens selected customer history', async () => {
    const customerName = '苏州工业园客户'
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/customers') {
        return {
          items: [
            {
              id: 7,
              name: customerName,
              region: '苏州',
              industry: '制造',
              opportunity_count: 4,
              last_activity_at: '2026-04-23T09:00:00'
            }
          ]
        }
      }
      if (path === `/api/customers/${encodeURIComponent(customerName)}/history`) {
        return {
          customer: { name: customerName },
          opportunities: [{ id: 11, title: '设备更新项目' }],
          activities: [{ id: 21, type: 'visit', note: '现场拜访' }],
          quotes: [{ id: 31, status: 'submitted', amount: 120000 }]
        }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(CustomersPage)
    await flushPromises()
    await wrapper.find('[data-test="customer-row-7"]').trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/customers')
    expect(apiMock.get).toHaveBeenCalledWith(`/api/customers/${encodeURIComponent(customerName)}/history`)
    expect(wrapper.text()).toContain(customerName)
    expect(wrapper.text()).toContain('设备更新项目')
    expect(wrapper.text()).toContain('现场拜访')
    expect(wrapper.text()).toContain('submitted')
    expect(wrapper.text()).not.toContain('昆山某单位')
  })

  it('goals page loads and refreshes weekly progress for the selected week', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path.startsWith('/api/goals/weekly-progress?week_start=')) {
        const weekStart = decodeURIComponent(path.split('week_start=')[1] ?? '')
        return { week_start: weekStart, visits: 8, quotes: 3, accepted_opportunities: 5 }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(GoalsPage)
    await flushPromises()
    await wrapper.find('[data-test="week-start"]').setValue('2026-04-27')
    await wrapper.find('[data-test="goals-form"]').trigger('submit')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/goals/weekly-progress?week_start=2026-04-27')
    expect(wrapper.text()).toContain('拜访')
    expect(wrapper.text()).toContain('8')
    expect(wrapper.text()).toContain('报价')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('有效商机')
    expect(wrapper.text()).toContain('5')
  })

  it('notifications page loads logs and reloads after sending a digest', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/notifications/logs') {
        return {
          items: [
            {
              id: 42,
              channel: 'dingtalk',
              template: 'daily_digest',
              status: 'failed',
              failure_reason: 'webhook timeout',
              candidate_ids: [1, 2],
              created_at: '2026-04-24T08:00:00'
            }
          ]
        }
      }
      throw new Error(`unexpected path ${path}`)
    })
    apiMock.post.mockResolvedValue({ ok: true })

    const wrapper = mount(NotificationsPage)
    await flushPromises()
    await wrapper.find('[data-test="send-digest"]').trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/notifications/logs')
    expect(apiMock.get).toHaveBeenCalledTimes(2)
    expect(apiMock.post).toHaveBeenCalledWith('/api/notifications/dingtalk/digest', { simulate_failure: false })
    expect(wrapper.text()).toContain('webhook timeout')
  })

  it('agents page renders backend agent capacity and heartbeat', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/agents') {
        return {
          items: [
            {
              agent_id: 'agent-ops',
              hostname: 'worker-01',
              status: 'connected',
              capacity: 3,
              active_sessions: 2,
              last_heartbeat_at: '2026-04-24T07:59:00'
            }
          ]
        }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(AgentsPage)
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/agents')
    expect(wrapper.text()).toContain('agent-ops')
    expect(wrapper.text()).toContain('worker-01')
    expect(wrapper.text()).toContain('2 / 3')
    expect(wrapper.text()).toContain('2026-04-24')
    expect(wrapper.text()).not.toContain('local-agent')
  })

  it('audit logs page renders backend audit entries', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/audit-logs') {
        return {
          items: [
            {
              id: 55,
              action: 'rule.activate',
              resource_type: 'source_rule',
              resource_id: 'source-1',
              actor_username: 'admin@example.com',
              created_at: '2026-04-24T10:00:00'
            }
          ]
        }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(AuditLogsPage)
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/api/audit-logs')
    expect(wrapper.text()).toContain('rule.activate')
    expect(wrapper.text()).toContain('source_rule')
    expect(wrapper.text()).toContain('source-1')
    expect(wrapper.text()).toContain('admin@example.com')
    expect(wrapper.text()).not.toContain('opportunity.review')
  })
})
