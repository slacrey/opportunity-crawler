import { defineStore } from 'pinia'
import type { RuntimeEvent } from '../api/events'

type RunState = {
  run_id: string
  source_id?: number
  status: string
  item_count?: number
}

export const useRuntimeStore = defineStore('runtime', {
  state: () => ({
    eventState: 'connected' as 'connected' | 'disconnected',
    runs: {} as Record<string, RunState>
  }),
  actions: {
    applyEvent(event: RuntimeEvent) {
      if (!event.run_id) return
      const status = event.type.replace(/^run_/, '')
      this.runs[event.run_id] = {
        ...this.runs[event.run_id],
        run_id: event.run_id,
        source_id: event.source_id,
        status,
        item_count: event.item_count ?? this.runs[event.run_id]?.item_count
      }
    }
  }
})

