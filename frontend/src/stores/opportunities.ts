import { defineStore } from 'pinia'
import { apiClient, type ApiClient } from '../api/client'

export type Candidate = {
  id: number
  title: string
  score: number
  priority_label?: string
  review_status: string
  follow_up_status?: string
  organization_name?: string | null
}

export type OpportunityDetail = {
  candidate: Candidate
  source?: Record<string, unknown> | null
  evidence?: Record<string, unknown> | null
  analysis?: Record<string, unknown> | null
}

export type ManualImportPayload = {
  source_id: number
  title: string
  body: string
  url?: string | null
  organization_name?: string | null
  region?: string | null
  industry?: string | null
  project_stage?: string | null
  budget_amount?: number | null
}

export const useOpportunitiesStore = defineStore('opportunities', {
  state: () => ({
    reviewQueue: [] as Candidate[],
    selected: null as Candidate | null,
    selectedDetail: null as OpportunityDetail | null,
    loading: false,
    error: null as string | null
  }),
  actions: {
    async loadReviewQueue(client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        const response = await client.get<{ items: Candidate[] }>('/api/opportunities?review_status=pending')
        this.reviewQueue = response.items
        return response.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载复核队列失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadDetail(candidateId: number, client: Pick<ApiClient, 'get'> = apiClient) {
      this.loading = true
      this.error = null
      try {
        this.selectedDetail = await client.get<OpportunityDetail>(`/api/opportunities/${candidateId}`)
        this.selected = this.selectedDetail.candidate
        return this.selectedDetail
      } catch (error) {
        this.error = error instanceof Error ? error.message : '加载商机详情失败'
        throw error
      } finally {
        this.loading = false
      }
    },
    async createManualImport(payload: ManualImportPayload, client: Pick<ApiClient, 'post'> = apiClient) {
      this.error = null
      try {
        const created = await client.post<Candidate>('/api/opportunities/manual-import', payload)
        if (created.review_status === 'pending' && !this.reviewQueue.some((candidate) => candidate.id === created.id)) {
          this.reviewQueue.unshift(created)
        }
        return created
      } catch (error) {
        this.error = error instanceof Error ? error.message : '手动导入失败'
        throw error
      }
    },
    async reviewCandidate(
      candidateId: number,
      reviewStatus: 'pending' | 'accepted' | 'rejected',
      client: Pick<ApiClient, 'post'> = apiClient
    ) {
      this.error = null
      const updated = await client.post<Candidate>(`/api/opportunities/${candidateId}/review`, {
        review_status: reviewStatus
      })
      const index = this.reviewQueue.findIndex((candidate) => candidate.id === candidateId)
      if (index >= 0) this.reviewQueue[index] = updated
      if (this.selected?.id === candidateId) this.selected = updated
      if (this.selectedDetail?.candidate.id === candidateId) this.selectedDetail.candidate = updated
      return updated
    },
    async updateFollowUp(
      candidateId: number,
      followUpStatus: string,
      note: string | null = null,
      client: Pick<ApiClient, 'post'> = apiClient
    ) {
      this.error = null
      try {
        const updated = await client.post<Candidate>(`/api/opportunities/${candidateId}/follow-up`, {
          follow_up_status: followUpStatus,
          note
        })
        const index = this.reviewQueue.findIndex((candidate) => candidate.id === candidateId)
        if (index >= 0) this.reviewQueue[index] = updated
        if (this.selected?.id === candidateId) this.selected = updated
        if (this.selectedDetail?.candidate.id === candidateId) this.selectedDetail.candidate = updated
        return updated
      } catch (error) {
        this.error = error instanceof Error ? error.message : '更新跟进状态失败'
        throw error
      }
    }
  }
})
