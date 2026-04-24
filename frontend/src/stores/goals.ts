import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type WeeklyProgress = {
  week_start: string
  accepted_opportunities: number
  visits: number
  quotes: number
}

export const useGoalsStore = defineStore('goals', {
  state: () => ({
    weeklyProgress: null as WeeklyProgress | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadWeeklyProgress(weekStart: string, client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        this.weeklyProgress = await client.get<WeeklyProgress>(
          `/api/goals/weekly-progress?week_start=${encodeURIComponent(weekStart)}`
        )
        return this.weeklyProgress
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载目标进度失败'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
