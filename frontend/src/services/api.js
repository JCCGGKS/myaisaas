// API 服务层
// 真实后端就绪后，把 .env 的 VITE_USE_MOCK 改为 false 即可切到真实接口。
// 接口约定见 AGENTS.md 的「关键 API」与「游客模式与渠道绑定」章节。

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true'

const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const uid = () =>
  (crypto.randomUUID && crypto.randomUUID()) ||
  `r_${Date.now()}_${Math.random().toString(36).slice(2)}`

// 模拟游客限额（见 AGENTS.md）：游客最多 1 雷达；
// 绑定跟随雷达，渠道限额按「单个雷达」计（演示默认每雷达最多 1 个渠道）
const GUEST_LIMIT = { radar: 1, channel_per_radar: 1 }

// ---------- mock 数据（无后端时演示用） ----------
const MOCK_RADARS = []
const MOCK_EVENTS = {}

const MOCK_CHANNELS = [
  { type: 'email', bound: false },
  { type: 'webpush', bound: false },
  { type: 'feishu', bound: false },
]

// 为雷达生成示例事件：即便未绑定渠道，事件流也能直接渲染到页面（用于演示/测试）
function mockEventsFor(radar) {
  const q = radar.raw_query || '监控目标'
  return [
    {
      id: uid(),
      radar_id: radar.id,
      title: `【示例】${q} —— 相关动态 #1`,
      source_url: 'https://example.com/event-1',
      relevance_score: 0.92,
      summarized: true,
      created_at: new Date(Date.now() - 120_000).toISOString(),
    },
    {
      id: uid(),
      radar_id: radar.id,
      title: `【示例】${q} —— 相关动态 #2`,
      source_url: 'https://example.com/event-2',
      relevance_score: 0.81,
      summarized: true,
      created_at: new Date(Date.now() - 600_000).toISOString(),
    },
  ]
}

function limitError(msg) {
  const err = new Error(msg)
  err.code = 'limit_exceeded'
  return err
}

// 结构化错误：携带后端返回的状态码与业务 code（如 limit_exceeded / 409 等）
class ApiError extends Error {
  constructor(message, { status, code } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// ---------- 真实请求封装 ----------
async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    // 必须带凭据，浏览器才会自动携带/存储后端下发的身份 cookie（wa_auth / wa_guest）。
    // 即便走 vite 代理同域也无害；跨域时（前端独立部署）这是必需的。
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let body = null
    let msg = `API ${res.status} ${res.statusText}`
    let code = null
    try {
      body = await res.json()
      msg = body?.detail || body?.message || msg
      code = body?.code || null
    } catch {
      /* ignore non-json error body */
    }
    if (res.status === 402 || code === 'limit_exceeded') {
      throw limitError('已达游客上限，请登录解锁更多')
    }
    throw new ApiError(msg, { status: res.status, code })
  }
  return res.json()
}

// ---------- 对外接口 ----------

// 创建雷达：自然语言 -> 后端 LLM 解析为结构化参数
// 注意：绑定跟随雷达（方案 B），创建时不携带任何渠道；
// 渠道在雷达创建后于卡片内单独绑定，且每个雷达相互独立、不继承其它雷达。
export async function createRadar(rawQuery) {
  if (!rawQuery || !rawQuery.trim()) throw new Error('监控目标不能为空')
  if (USE_MOCK) {
    await delay(600)
    if (MOCK_RADARS.length >= GUEST_LIMIT.radar) {
      throw limitError('游客最多创建 1 个雷达，登录解锁更多')
    }
    const radar = {
      id: uid(),
      raw_query: rawQuery.trim(),
      keywords: [],
      sources: [],
      notify_channels: [], // 绑定跟随雷达：默认空，创建后单独绑定
      active: true,
      created_at: new Date().toISOString(),
    }
    MOCK_RADARS.unshift(radar)
    // 未绑渠道也生成示例事件，便于直接看到事件流渲染
    MOCK_EVENTS[radar.id] = mockEventsFor(radar)
    return radar
  }
  // 真实后端期望 notify_channels（多通道列表），与 AGENTS.md 一致；此处留空
  return request('/radars', {
    method: 'POST',
    body: JSON.stringify({
      raw_query: rawQuery.trim(),
      notify_channels: [],
    }),
  })
}

// 我的雷达列表
export async function listRadars() {
  if (USE_MOCK) {
    await delay(300)
    return MOCK_RADARS
  }
  return request('/radars')
}

// 某个雷达的事件流
export async function listEvents(radarId) {
  if (USE_MOCK) {
    await delay(300)
    return MOCK_EVENTS[radarId] || []
  }
  return request(`/radars/${radarId}/events`)
}

// 可用渠道 + 绑定状态（渠道无关，见 AGENTS.md）
// radarId 非空时按该雷达的真实绑定标注 bound/verified/recipient（绑定跟随雷达）
export async function listChannels(radarId = null) {
  if (USE_MOCK) {
    await delay(200)
    const radar = radarId != null ? MOCK_RADARS.find((r) => r.id === radarId) : null
    const bound = new Set((radar?.notify_channels || []).map((b) => b.channel_type))
    return MOCK_CHANNELS.map((c) => ({
      type: c.type,
      bound: bound.has(c.type),
      verified: (radar?.notify_channels || []).some((b) => b.channel_type === c.type && b.verified),
      recipient:
        (radar?.notify_channels || []).find((b) => b.channel_type === c.type)?.recipient || null,
    }))
  }
  const qs = radarId != null ? `?radar_id=${encodeURIComponent(radarId)}` : ''
  return request(`/channels${qs}`)
}

// 绑定渠道（跟随雷达）：必须指定 radarId；email/webhook 提交 recipient
export async function bindChannel(radarId, type, recipient = '') {
  if (USE_MOCK) {
    await delay(500)
    const radar = MOCK_RADARS.find((r) => r.id === radarId)
    if (!radar) throw new Error('雷达不存在')
    // 游客按「单个雷达」计渠道限额
    const count = (radar.notify_channels || []).length
    if (count >= GUEST_LIMIT.channel_per_radar) {
      throw limitError(`游客每个雷达最多绑定 ${GUEST_LIMIT.channel_per_radar} 个渠道，登录解锁更多`)
    }
    const list = radar.notify_channels || (radar.notify_channels = [])
    if (!list.some((b) => b.channel_type === type)) {
      list.push({ channel_type: type, recipient: recipient || '', verified: true })
    }
    return { type, bound: true, verified: true }
  }
  return request(`/channels/${type}/bind`, {
    method: 'POST',
    body: JSON.stringify({ recipient: recipient || '', radar_id: radarId }),
  })
}

// 解绑渠道（跟随雷达）：从指定雷达移除该渠道
export async function unbindChannel(radarId, type) {
  if (USE_MOCK) {
    await delay(400)
    const radar = MOCK_RADARS.find((r) => r.id === radarId)
    if (radar?.notify_channels) {
      radar.notify_channels = radar.notify_channels.filter((b) => b.channel_type !== type)
    }
    return { type, bound: false, verified: false }
  }
  return request(`/radars/${radarId}/channels/${type}`, { method: 'DELETE' })
}

// 获取 VAPID 公钥（Web Push 订阅用 applicationServerKey）
export async function getVapidPublicKey() {
  if (USE_MOCK) return '' // mock 模式无需真实密钥
  const data = await request('/channels/vapid-public-key')
  return data.vapid_public_key || ''
}

// 删除雷达（联删其事件）：路由 DELETE /radars/:id
export async function deleteRadar(radarId) {
  if (USE_MOCK) {
    return { ok: true }
  }
  return request(`/radars/${radarId}`, { method: 'DELETE' })
}

// ---------- 鉴权（JWT，cookie 自动携带/写入） ----------
// 说明：注册/登录本质是把「当前游客」升级为账号，后端会把游客的雷达与渠道
// 合并进账号并写入 wa_uid（JWT）cookie。前端无需手动管理 token，依赖 cookie 即可。
export async function register(name, email, password) {
  if (USE_MOCK) {
    return { user_id: 'mock', is_guest: false }
  }
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name: name || '', email, password }),
  })
}

export async function login(email, password) {
  if (USE_MOCK) {
    return { user_id: 'mock', is_guest: false }
  }
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

// 当前用户状态：游客（is_guest=true，无 email）或已登录账号（is_guest=false）
export async function getMe() {
  if (USE_MOCK) {
    return { user_id: 'mock', email: null, is_guest: true }
  }
  return request('/auth/me')
}

export async function logout() {
  if (USE_MOCK) {
    return { ok: true }
  }
  return request('/auth/logout', { method: 'POST' })
}
