// Web Push（浏览器原生通知）封装
// 流程：请求通知权限 -> 注册 Service Worker -> pushManager.subscribe -> 把订阅信息交给 bindFn
import { getVapidPublicKey, bindChannel } from './api.js'

const SW_URL = '/sw.js'

// base64url -> Uint8Array（applicationServerKey 必须是 Uint8Array）
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

export function isPushSupported() {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

// 注册并订阅 Web Push，随后把订阅 JSON 交给 bindFn(radarId, subscriptionJson)
// bindFn 默认复用 bindChannel，便于复用「绑定跟随雷达」逻辑。
export async function registerPush(radarId, bindFn = bindChannel) {
  if (!isPushSupported()) {
    throw new Error(
      '当前环境不支持 Web Push：Service Worker 与通知 API 仅在 http://localhost 或 https 下可用。请改用 localhost 访问前端（不要用局域网 IP），并确认浏览器未禁用通知。'
    )
  }
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('需要通知权限才能订阅浏览器推送')
  }
  await navigator.serviceWorker.register(SW_URL)
  await navigator.serviceWorker.ready

  const publicKey = await getVapidPublicKey()
  let sub
  if (!publicKey) {
    // mock 模式（无真实 VAPID 公钥 / 无后端）：构造占位 subscription 直接绑定，
    // 不真正调用浏览器 pushManager.subscribe（其需真实密钥与服务）。
    sub = { endpoint: 'https://mock.push.local/subscription', keys: { p256dh: 'mock', auth: 'mock' } }
  } else {
    const registration = await navigator.serviceWorker.getRegistration()
    sub = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    })
  }
  // bindFn 约定为 (radarId, type, recipient)；webpush 的订阅 JSON 作为 recipient 传入。
  await bindFn(radarId, 'webpush', JSON.stringify(sub))
  return sub
}
