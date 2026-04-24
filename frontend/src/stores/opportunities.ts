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

export const useOpportunitiesStore = defineStore('opportunities', {
  state: () => ({
    reviewQueue: [] as Candidate[],
    selected: null as Candidate | null
  }),
  actions: {
    async reviewCandidate(
      candidateId: number,
      reviewStatus: 'pending' | 'accepted' | 'rejected',
      client: Pick<ApiClient, 'post'> = apiClient
    ) {
      const updated = await client.post<Candidate>(`/api/opportunities/${candidateId}/review`, {
        review_status: reviewStatus
      })
      const index = this.reviewQueue.findIndex((candidate) => candidate.id === candidateId)
      if (index >= 0) this.reviewQueue[index] = updated
      if (this.selected?.id === candidateId) this.selected = updated
      return updated
    }
  }
})

