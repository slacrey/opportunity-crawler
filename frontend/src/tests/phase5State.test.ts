import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, createApiClient } from '../api/client'
import NotificationsPage from '../pages/NotificationsPage.vue'
import ReviewQueuePage from '../pages/ReviewQueuePage.vue'
import SourcesPage from '../pages/SourcesPage.vue'
import { enforceAuthGuard } from '../router'
import { useAuthStore } from '../stores/auth'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn()
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    apiClient: apiMock
  }
})

describe('phase 5 control panel state handling', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.patch.mockReset()
  })

  it('auth store restores current user, evaluates permissions, and clears expired sessions', async () => {
    const auth = useAuthStore()
    localStorage.setItem('opportunity_crawler_token', 'token-1')
    auth.token = 'token-1'
    apiMock.get.mockResolvedValueOnce({
      user: { id: 1, username: 'biz', roles: ['business_manager'] }
    })

    await auth.loadCurrentUser()

    expect(apiMock.get).toHaveBeenCalledWith('/api/auth/me')
    expect(auth.user?.username).toBe('biz')
    expect(auth.can('opportunities:review')).toBe(true)
    expect(auth.can('source.advanced_rules:update')).toBe(false)

    auth.clearSession()

    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('opportunity_crawler_token')).toBeNull()
  })

  it('api client reports unauthorized responses so the app can redirect to login', async () => {
    const onUnauthorized = vi.fn()
    const client = createApiClient({
      onUnauthorized,
      fetcher: async () =>
        new Response(JSON.stringify({ error: { code: 'not_authenticated', message: 'Authentication required' } }), {
          status: 401,
          headers: { 'content-type': 'application/json' }
        })
    })

    await expect(client.get('/api/sources')).rejects.toMatchObject({
      code: 'not_authenticated',
      status: 401
    } satisfies Partial<ApiError>)

    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('route guard redirects unauthenticated users and loads current profile for stored tokens', async () => {
    const auth = useAuthStore()

    expect(await enforceAuthGuard(fakeRoute('/sources'))).toEqual({
      path: '/login',
      query: { redirect: '/sources' }
    })

    auth.token = 'token-1'
    apiMock.get.mockResolvedValueOnce({
      user: { id: 1, username: 'manager', roles: ['manager'] }
    })

    expect(await enforceAuthGuard(fakeRoute('/goals', 'goals:read'))).toBe(true)
    expect(auth.user?.username).toBe('manager')
    expect(await enforceAuthGuard(fakeRoute('/review', 'opportunities:review'))).toEqual({ path: '/' })
  })

  it('review page hides unauthorized actions and prevents duplicate manual import submissions', async () => {
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'biz', roles: ['business_manager'] }
    apiMock.get.mockResolvedValueOnce({
      items: [{ id: 1, title: '昆山 AI 项目', organization_name: '昆山客户', score: 91, review_status: 'pending' }]
    })
    let resolveCreate: (value: unknown) => void = () => undefined
    apiMock.post.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        })
    )

    const wrapper = mount(ReviewQueuePage)
    await flushPromises()
    await wrapper.find('[data-test="manual-title"]').setValue('新项目')
    await wrapper.find('[data-test="manual-body"]').setValue('正文')
    await wrapper.find('[data-test="manual-import"]').trigger('submit')
    await wrapper.find('[data-test="manual-import"]').trigger('submit')

    expect(apiMock.post).toHaveBeenCalledTimes(1)
    resolveCreate({ id: 2, title: '新项目', score: 70, review_status: 'pending' })
    await flushPromises()

    auth.user = { id: 2, username: 'manager', roles: ['manager'] }
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-test="manual-submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-test="accept-1"]').attributes('disabled')).toBeDefined()
  })

  it('sources page gates advanced rule actions while allowing basic rule edits', async () => {
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'biz', roles: ['business_manager'] }
    apiMock.get.mockImplementation(async (path: string) => {
      if (path === '/api/sources') {
        return {
          items: [{ id: 1, name: '中国政府采购网', adapter_mode: 'manual_import', login_status: 'not_required' }]
        }
      }
      if (path === '/api/sources/1') {
        return {
          source: { id: 1, name: '中国政府采购网', adapter_mode: 'manual_import' },
          basic_rules: { regions: ['昆山'], demand_keywords: ['AI'], frequency: 'daily' },
          active_rule: { version: 1, status: 'active' }
        }
      }
      if (path === '/api/sources/1/advanced-rules') {
        return { items: [{ version: 1, status: 'active' }] }
      }
      throw new Error(`unexpected path ${path}`)
    })

    const wrapper = mount(SourcesPage)
    await flushPromises()
    await wrapper.find('[data-test="source-row-1"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-test="basic-rules-save"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('[data-test="preview"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-test="activate"]').attributes('disabled')).toBeDefined()
  })

  it('notifications page prevents duplicate digest submissions', async () => {
    const auth = useAuthStore()
    auth.token = 'token-1'
    auth.user = { id: 1, username: 'manager', roles: ['manager'] }
    apiMock.get.mockResolvedValue({ items: [] })
    let resolveDigest: (value: unknown) => void = () => undefined
    apiMock.post.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveDigest = resolve
        })
    )

    const wrapper = mount(NotificationsPage)
    await flushPromises()
    await wrapper.find('[data-test="send-digest"]').trigger('click')
    await wrapper.find('[data-test="send-digest"]').trigger('click')

    expect(apiMock.post).toHaveBeenCalledTimes(1)
    resolveDigest({ ok: true })
    await flushPromises()
  })
})

function fakeRoute(path: string, permission?: string) {
  return {
    path,
    fullPath: path,
    matched: [{ meta: { requiresAuth: path !== '/login' } }],
    meta: permission ? { permission } : {}
  } as any
}
