import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SourcesPage from '../pages/SourcesPage.vue'
import { useAuthStore } from '../stores/auth'
import { useSourcesStore } from '../stores/sources'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn()
}))

vi.mock('../api/client', () => ({
  apiClient: apiMock,
  API_PATH_PREFIX: '/api/'
}))

describe('sources store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.patch.mockReset()
  })

  it('updates basic rules through json api', async () => {
    const sources = useSourcesStore()

    await sources.updateBasicRules(
      1,
      { regions: ['昆山'], demand_keywords: ['AI'], frequency: 'daily' },
      { patch: async (_path: string, payload: unknown) => ({ id: 1, ...payload }) }
    )

    expect(sources.lastRuleUpdate?.regions).toEqual(['昆山'])
    expect(sources.lastRuleUpdate?.frequency).toBe('daily')
  })

  it('starts collection from the selected source row', async () => {
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'admin', roles: ['administrator'] }
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/sources') {
        return {
          items: [
            {
              id: 1,
              name: '中国政府采购网',
              adapter_mode: 'public_search_list_detail',
              login_status: 'not_required',
              health_status: 'unknown'
            }
          ]
        }
      }
      if (path === '/api/sources/1') {
        return {
          source: { id: 1, name: '中国政府采购网', adapter_mode: 'public_search_list_detail' },
          basic_rules: { frequency: 'daily' },
          active_rule: { version: 1, status: 'active' }
        }
      }
      if (path === '/api/sources/1/advanced-rules') {
        return { items: [{ version: 1, status: 'active' }] }
      }
      throw new Error(`unexpected path ${path}`)
    })
    apiMock.post.mockImplementation(async (path: string) => {
      if (path === '/api/sources/1/collection-runs') {
        return {
          run: {
            run_id: 'run-from-source-page',
            source_id: 1,
            source_name: '中国政府采购网',
            status: 'queued',
            item_count: 0
          }
        }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(SourcesPage)
    await flushPromises()

    const startButton = wrapper.get('[data-test="start-collection"]')
    expect(startButton.attributes('disabled')).toBeDefined()

    await wrapper.get('[data-test="source-row-1"]').trigger('click')
    await flushPromises()
    await startButton.trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/api/sources/1/collection-runs')
    expect(wrapper.text()).toContain('采集已启动：run-from-source-page')
  })
})
