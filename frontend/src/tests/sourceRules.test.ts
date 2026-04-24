import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useSourcesStore } from '../stores/sources'

describe('sources store', () => {
  beforeEach(() => setActivePinia(createPinia()))

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
})

