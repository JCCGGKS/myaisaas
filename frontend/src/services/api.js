// API 服务层
// 真实后端就绪后，把 .env 的 VITE_USE_MOCK 改为 false 即可切到真实接口。
// 接口约定见 AGENTS.md 的「关键 API」与「游客模式与渠道绑定」章节。

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true'

const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const uid = () =>
  (crypto.randomUUID && crypto.randomUUID()) ||
  `r_${Date.now()}_${Math.random().toString(36).slice(2)}`

// 模拟游客限额（见 AGENTS.md）：游客最多 1 雷达；演示用允许多渠道绑定（达到上限弹窗）
const GUEST_LIMIT = { radar: 1, channel: 3 }

// ---------- mock 数据（无后端时演示用） ----------
const MOCK_RADARS = []
const MOCK_EVENTS = {}

const MOCK_CHANNELS = [
  { type: 'telegram', bound: false },
  { type: 'email', bound: false },
  { type: 'webhook', bound: false },
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
// notifyChannel：创建时传入已绑定的推送渠道类型；未绑定时为空值占位（表示未绑定）
export async function createRadar(rawQuery, notifyChannel = '') {
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
      notify_channel: notifyChannel,
      channels: notifyChannel ? [notifyChannel] : [],
      active: true,
      created_at: new Date().toISOString(),
    }
    MOCK_RADARS.unshift(radar)
    // 未绑渠道也生成示例事件，便于直接看到事件流渲染
    MOCK_EVENTS[radar.id] = mockEventsFor(radar)
    return radar
  }
  // 真实后端期望 notify_channels（多通道列表），与 AGENTS.md 一致
  return request('/radars', {
    method: 'POST',
    body: JSON.stringify({
      raw_query: rawQuery.trim(),
      notify_channels: notifyChannel ? [notifyChannel] : [],
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
export async function listChannels() {
  if (USE_MOCK) {
    await delay(200)
    return MOCK_CHANNELS.map((c) => ({ ...c }))
  }
  return request('/channels')
}

// 绑定渠道：email/webhook 直接提交 recipient；telegram 返回 connect_url
export async function bindChannel(type, recipient) {
  if (USE_MOCK) {
    await delay(500)
    const bound = MOCK_CHANNELS.filter((c) => c.bound).length
    if (bound >= GUEST_LIMIT.channel) {
      throw limitError(`游客最多绑定 ${GUEST_LIMIT.channel} 个渠道，登录解锁更多`)
    }
    const c = MOCK_CHANNELS.find((x) => x.type === type)
    if (!c) throw new Error(`unknown channel: ${type}`)
    c.bound = true
    // 模拟后端行为：把渠道加入每个雷达的 channels 列表（多通道），去重
    MOCK_RADARS.forEach((r) => {
      if (!r.channels) r.channels = []
      if (!r.channels.includes(type)) r.channels.push(type)
    })
    return { ...c }
  }
  return request(`/channels/${type}/bind`, {
    method: 'POST',
    body: JSON.stringify({ recipient: recipient || '' }),
  })
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
    return { user_id: 'mock', email: null, is_guest: true, channel_bindings: [] }
  }
  return request('/auth/me')
}

export async function logout() {
  if (USE_MOCK) {
    return { ok: true }
  }
  return request('/auth/logout', { method: 'POST' })
}
