import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DashboardPage from '../pages/DashboardPage.vue'
import OpportunityDetailPage from '../pages/OpportunityDetailPage.vue'
import ReviewQueuePage from '../pages/ReviewQueuePage.vue'
import SourcesPage from '../pages/SourcesPage.vue'
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

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '1' } })
}))

describe('core control panel pages', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'admin', roles: ['administrator'] }
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.patch.mockReset()
  })

  it('dashboard renders real summary and runtime rows from stores', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/dashboard/summary') {
        return {
          sources: { total: 4, healthy: 2, failed: 1, login_required: 1 },
          opportunities: { pending: 3, accepted: 1, high_score: 2 },
          runs: { running: 1, failed: 1 },
          agents: { online: 1 }
        }
      }
      if (path === '/api/collection-runs') {
        return { items: [{ run_id: 'run-1', source_name: '中国政府采购网', status: 'failed', item_count: 3 }] }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(DashboardPage)
    await flushPromises()

    expect(wrapper.text()).toContain('待复核')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('run-1')
    expect(wrapper.text()).not.toContain('暂无运行记录')
  })

  it('sources page loads real sources and opens source rules without fallback records', async () => {
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/sources') {
        return {
          items: [
            {
              id: 1,
              name: '中国政府采购网',
              adapter_mode: 'public_search_list_detail',
              login_status: 'not_required',
              health_status: 'healthy'
            }
          ]
        }
      }
      if (path === '/api/sources/1') {
        return {
          source: { id: 1, name: '中国政府采购网', health_status: 'healthy' },
          basic_rules: { regions: ['昆山'], demand_keywords: ['AI'], frequency: 'daily' },
          active_rule: { version: 1, status: 'active' }
        }
      }
      if (path === '/api/sources/1/advanced-rules') {
        return { items: [{ version: 1, status: 'active', selectors: { list_selector: '.item' } }] }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(SourcesPage)
    await flushPromises()
    await wrapper.find('[data-test="source-row-1"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('中国政府采购网')
    expect(wrapper.text()).toContain('采集规则')
    expect(wrapper.text()).toContain('version 1')
    expect(wrapper.text()).not.toContain('建设网')
  })

  it('review queue loads candidates, imports manually, and reviews candidates', async () => {
    apiMock.get.mockResolvedValueOnce({
      items: [{ id: 1, title: '昆山 AI 项目', organization_name: '昆山某单位', score: 91, review_status: 'pending' }]
    })
    apiMock.post.mockImplementation(async (path: string) => {
      if (path === '/api/opportunities/manual-import') {
        return { id: 2, title: '新导入项目', score: 70, review_status: 'pending' }
      }
      if (path === '/api/opportunities/1/review') {
        return { id: 1, title: '昆山 AI 项目', organization_name: '昆山某单位', score: 91, review_status: 'accepted' }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(ReviewQueuePage)
    await flushPromises()
    await wrapper.find('[data-test="manual-title"]').setValue('新导入项目')
    await wrapper.find('[data-test="manual-body"]').setValue('昆山 数字化 项目正文')
    await wrapper.find('[data-test="manual-import"]').trigger('submit')
    await flushPromises()
    await wrapper.find('[data-test="accept-1"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('新导入项目')
    expect(wrapper.text()).toContain('accepted')
    expect(wrapper.text()).not.toContain('昆山 AI 云平台采购意向')
  })

  it('opportunity detail loads detail and updates follow-up status', async () => {
    apiMock.get.mockResolvedValueOnce({
      candidate: {
        id: 1,
        title: '昆山 AI 项目',
        organization_name: '昆山某单位',
        score: 91,
        priority_label: 'P0',
        review_status: 'accepted',
        follow_up_status: 'none'
      },
      source: { name: '微信公众号手动导入' },
      evidence: { url: 'https://example.test/1', raw_text: '昆山 AI 项目正文' },
      analysis: { scoring_reasons: ['命中昆山', '预算较高'] }
    })
    apiMock.post.mockResolvedValueOnce({
      id: 1,
      title: '昆山 AI 项目',
      score: 91,
      review_status: 'accepted',
      follow_up_status: 'visited'
    })

    const wrapper = mount(OpportunityDetailPage)
    await flushPromises()
    await wrapper.find('[data-test="follow-up-status"]').setValue('visited')
    await wrapper.find('[data-test="follow-up-note"]').setValue('已拜访')
    await wrapper.find('[data-test="follow-up-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('昆山 AI 项目')
    expect(wrapper.text()).toContain('微信公众号手动导入')
    expect(wrapper.text()).toContain('visited')
    expect(apiMock.post).toHaveBeenCalledWith('/api/opportunities/1/follow-up', {
      follow_up_status: 'visited',
      note: '已拜访'
    })
  })
})
