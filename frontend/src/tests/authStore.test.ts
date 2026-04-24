import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '../stores/auth'

describe('auth store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('stores token and role-aware user profile after login', async () => {
    const auth = useAuthStore()

    await auth.login(
      'admin',
      'admin-pass',
      {
        post: async () => ({
          access_token: 'token-1',
          user: { id: 1, username: 'admin', roles: ['administrator'] }
        })
      }
    )

    expect(auth.token).toBe('token-1')
    expect(auth.hasRole('administrator')).toBe(true)
  })
})

