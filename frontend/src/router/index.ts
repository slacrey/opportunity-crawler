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

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage },
    {
      path: '/',
      component: AdminLayout,
      children: [
        { path: '', component: DashboardPage },
        { path: 'sources', component: SourcesPage },
        { path: 'runs', component: CollectionRunsPage },
        { path: 'review', component: ReviewQueuePage },
        { path: 'opportunities/:id', component: OpportunityDetailPage },
        { path: 'customers', component: CustomersPage },
        { path: 'goals', component: GoalsPage },
        { path: 'notifications', component: NotificationsPage },
        { path: 'agents', component: AgentsPage },
        { path: 'audit', component: AuditLogsPage }
      ]
    }
  ]
})

