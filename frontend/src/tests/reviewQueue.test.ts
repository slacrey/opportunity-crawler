import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useOpportunitiesStore } from '../stores/opportunities'

describe('opportunities store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('accepts a candidate and updates local review queue state', async () => {
    const opportunities = useOpportunitiesStore()
    opportunities.reviewQueue = [{ id: 1, title: '昆山 AI 项目', review_status: 'pending', score: 91 }]

    await opportunities.reviewCandidate(1, 'accepted', {
      post: async () => ({ id: 1, title: '昆山 AI 项目', review_status: 'accepted', score: 91 })
    })

    expect(opportunities.reviewQueue[0].review_status).toBe('accepted')
  })
})

