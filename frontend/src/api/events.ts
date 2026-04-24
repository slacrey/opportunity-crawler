export type RuntimeEvent = {
  type: string
  run_id?: string
  source_id?: number
  item_count?: number
  status?: string
}

export function subscribeRuntimeEvents(onEvent: (event: RuntimeEvent) => void): () => void {
  const eventUrl = import.meta.env.VITE_EVENT_STREAM_URL ?? '/api/events'
  const source = new EventSource(eventUrl)
  source.addEventListener('snapshot', (event) => onEvent(JSON.parse((event as MessageEvent).data)))
  source.addEventListener('message', (event) => onEvent(JSON.parse((event as MessageEvent).data)))
  return () => source.close()
}

