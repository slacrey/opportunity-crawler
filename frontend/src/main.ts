import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/theme.css'
import App from './App.vue'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()

createApp(App).use(pinia).use(router).use(ElementPlus).mount('#app')

window.addEventListener('opportunity-crawler:auth-expired', () => {
  const auth = useAuthStore()
  auth.clearSession()
  const current = router.currentRoute.value
  if (current.path !== '/login') {
    void router.push({ path: '/login', query: { expired: '1', redirect: current.fullPath } })
  }
})
