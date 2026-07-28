import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import './style.css'

const app = createApp(App)

// Scroll-reveal directive: adds .is-in when element enters viewport
app.directive('reveal', {
  mounted(el, binding) {
    const delay = binding.value || 0
    if (delay) el.setAttribute('data-delay', String(delay))
    el.classList.add('reveal')
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-in')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' }
    )
    io.observe(el)
    el._io = io
  },
  unmounted(el) {
    if (el._io) el._io.disconnect()
  }
})

app.use(router)
app.mount('#app')

// 注册 Service Worker（Web Push 收通知用）。失败不影响页面其余功能。
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}
