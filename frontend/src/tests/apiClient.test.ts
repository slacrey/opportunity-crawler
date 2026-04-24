import { describe, expect, it } from 'vitest'
import { ApiError, createApiClient } from '../api/client'

describe('api client', () => {
  it('prefixes api base url and sends bearer token', async () => {
    const calls: RequestInit[] = []
    const client = createApiClient({
      baseUrl: 'http://127.0.0.1:8000',
      tokenProvider: () => 'token-1',
      fetcher: async (_url, init) => {
        calls.push(init ?? {})
        return new Response(JSON.stringify({ ok: true }), { status: 200 })
      }
    })

    const result = await client.get('/api/sources')

    expect(result).toEqual({ ok: true })
    expect(calls[0].headers).toMatchObject({ Authorization: 'Bearer token-1' })
  })

  it('throws structured api errors', async () => {
    const client = createApiClient({
      baseUrl: '',
      fetcher: async () =>
        new Response(JSON.stringify({ error: { code: 'permission_denied', message: 'Permission denied' } }), {
          status: 403
        })
    })

    await expect(client.post('/api/opportunities/1/review', {})).rejects.toMatchObject({
      code: 'permission_denied',
      status: 403
    } satisfies Partial<ApiError>)
  })
})

