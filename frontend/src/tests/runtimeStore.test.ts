import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useRuntimeStore } from '../stores/runtime'

describe('runtime store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('updates collection run state from runtime events', () => {
    const runtime = useRuntimeStore()

    runtime.applyEvent({ type: 'run_started', run_id: 'run-1', source_id: 1 })
    runtime.applyEvent({ type: 'run_succeeded', run_id: 'run-1', source_id: 1, item_count: 2 })

    expect(runtime.runs['run-1'].status).toBe('succeeded')
    expect(runtime.runs['run-1'].item_count).toBe(2)
  })
})

