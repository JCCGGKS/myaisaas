// Watch Anything — Service Worker（Web Push 通知）
// 监听推送事件并展示通知；点击通知打开对应链接。

self.addEventListener('push', (event) => {
  let data = { title: 'Watch Anything', body: '', url: '/' }
  if (event.data) {
    try {
      data = Object.assign(data, event.data.json())
    } catch (e) {
      // 非 JSON 载荷：当作纯文本
      data.body = event.data.text()
    }
  }
  const options = {
    body: data.body || '',
    data: { url: data.url || '/' },
    badge: '/badge.png',
    icon: '/icon.png',
  }
  event.waitUntil(self.registration.showNotification(data.title || 'Watch Anything', options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((winClients) => {
      for (const client of winClients) {
        if ('focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      if (clients.openWindow) return clients.openWindow(url)
    })
  )
})
