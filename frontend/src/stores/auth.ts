import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

type UserProfile = {
  id: number
  username: string
  roles: string[]
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: readStoredToken(),
    user: null as UserProfile | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async login(username: string, password: string, client: Pick<ApiClient, 'post'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const result = await client.post<{ access_token: string; user: UserProfile }>('/api/auth/login', {
          username,
          password
        })
        this.token = result.access_token
        this.user = result.user
        writeStoredToken(result.access_token)
      } catch (error) {
        this.error = error instanceof Error ? error.message : '登录失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    hasRole(role: string) {
      return Boolean(this.user?.roles.includes(role))
    }
  }
})

function readStoredToken() {
  if (typeof localStorage === 'undefined') return null
  return localStorage.getItem('opportunity_crawler_token')
}

function writeStoredToken(token: string) {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('opportunity_crawler_token', token)
  }
}
