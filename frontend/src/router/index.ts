import { createRouter, createWebHistory } from 'vue-router'
import AdminLayout from '../layouts/AdminLayout.vue'
import LoginPage from '../pages/LoginPage.vue'
import DashboardPage from '../pages/DashboardPage.vue'
import SourcesPage from '../pages/SourcesPage.vue'
import CollectionRunsPage from '../pages/CollectionRunsPage.vue'
import ReviewQueuePage from '../pages/ReviewQueuePage.vue'
import OpportunityDetailPage from '../pages/OpportunityDetailPage.vue'
import CustomersPage from '../pages/CustomersPage.vue'
import GoalsPage from '../pages/GoalsPage.vue'
import NotificationsPage from '../pages/NotificationsPage.vue'
import AgentsPage from '../pages/AgentsPage.vue'
import AuditLogsPage from '../pages/AuditLogsPage.vue'
import { useAuthStore } from '../stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage },
    {
      path: '/',
      component: AdminLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', component: DashboardPage },
        { path: 'sources', component: SourcesPage },
        { path: 'runs', component: CollectionRunsPage },
        { path: 'review', component: ReviewQueuePage, meta: { permission: 'opportunities:review' } },
        { path: 'opportunities/:id', component: OpportunityDetailPage, meta: { permission: 'opportunities:review' } },
        { path: 'customers', component: CustomersPage, meta: { permission: 'opportunities:review' } },
        { path: 'goals', component: GoalsPage, meta: { permission: 'goals:read' } },
        { path: 'notifications', component: NotificationsPage, meta: { permission: 'notifications:read' } },
        { path: 'agents', component: AgentsPage },
        { path: 'audit', component: AuditLogsPage }
      ]
    }
  ]
})

router.beforeEach(enforceAuthGuard)

export async function enforceAuthGuard(to: {
  path: string
  fullPath: string
  matched: Array<{ meta: Record<string, unknown> }>
  meta: Record<string, unknown>
}) {
  if (to.path === '/login') return true
  if (!to.matched.some((record) => record.meta.requiresAuth)) return true

  const auth = useAuthStore()
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (!auth.user) {
    try {
      await auth.loadCurrentUser()
    } catch {
      return { path: '/login', query: { expired: '1', redirect: to.fullPath } }
    }
  }

  const permission = typeof to.meta.permission === 'string' ? to.meta.permission : null
  if (permission && !auth.can(permission)) {
    return { path: '/' }
  }

  return true
}
