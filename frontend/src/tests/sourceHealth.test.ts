import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useSourcesStore } from '../stores/sources'

describe('source health summary', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('counts healthy, failed, and login-required sources for dashboard badges', () => {
    const sources = useSourcesStore()
    sources.items = [
      { id: 1, name: '中国政府采购网', health_status: 'healthy', login_status: 'not_required' },
      { id: 2, name: '建设网', health_status: 'unknown', login_status: 'pending_login' },
      { id: 3, name: '示例站点', health_status: 'failed', login_status: 'not_required' }
    ]

    expect(sources.healthSummary).toEqual({ healthy: 1, failed: 1, loginRequired: 1 })
  })
})

