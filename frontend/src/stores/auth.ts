import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type UserProfile = {
  id: number
  username: string
  roles: string[]
}

const ROLE_PERMISSIONS: Record<string, Set<string>> = {
  operator: new Set(['source:read', 'source.basic_rules:update', 'collection_runs:manage', 'agents:read']),
  business_manager: new Set(['source:read', 'source.basic_rules:update', 'opportunities:review', 'opportunities:write']),
  manager: new Set(['source:read', 'opportunities:read', 'goals:read', 'notifications:read']),
  administrator: new Set(['*'])
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: readStoredToken(),
    user: null as UserProfile | null,
    loading: false,
    error: null as string | null
  }),
  getters: {
    isAuthenticated(state) {
      return Boolean(state.token)
    }
  },
  actions: {
    async login(username: string, password: string, client: Pick<ApiClient, 'post'> = apiClient) {
      if (this.loading) return
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
    async loadCurrentUser(client: Pick<ApiClient, 'get'> = apiClient) {
      if (!this.token) return null
      this.loading = true
      this.error = null
      try {
        const result = await client.get<{ user: UserProfile }>('/api/auth/me')
        this.user = result.user
        return result.user
      } catch (error) {
        this.clearSession()
        this.error = error instanceof Error ? error.message : '登录已过期'
        throw error
      } finally {
        this.loading = false
      }
    },
    clearSession() {
      this.token = null
      this.user = null
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('opportunity_crawler_token')
      }
    },
    hasRole(role: string) {
      return Boolean(this.user?.roles.includes(role))
    },
    can(permission: string) {
      return Boolean(
        this.user?.roles.some((role) => {
          const permissions = ROLE_PERMISSIONS[role]
          return permissions?.has('*') || permissions?.has(permission)
        })
      )
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
