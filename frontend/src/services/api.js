// API 服务层
// 真实后端就绪后，把 .env 的 VITE_USE_MOCK 改为 false 即可切到真实接口。
// 接口约定见 AGENTS.md 的「关键 API」与「游客模式与渠道绑定」章节。

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true'

const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const uid = () =>
  (crypto.randomUUID && crypto.randomUUID()) ||
  `r_${Date.now()}_${Math.random().toString(36).slice(2)}`

// 模拟游客限额（见 AGENTS.md）：游客最多 1 雷达 / 1 渠道
const GUEST_LIMIT = { radar: 1, channel: 1 }

// ---------- mock 数据（无后端时演示用） ----------
const MOCK_RADARS = []
const MOCK_EVENTS = {}

const MOCK_CHANNELS = [
  { type: 'telegram', bound: false },
  { type: 'email', bound: false },
  { type: 'webhook', bound: false },
]

function limitError(msg) {
  const err = new Error(msg)
  err.code = 'limit_exceeded'
  return err
}

// ---------- 真实请求封装 ----------
async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let code = null
    try {
      const body = await res.json()
      code = body?.code || null
    } catch {
      /* ignore non-json error body */
    }
    if (res.status === 402 || code === 'limit_exceeded') {
      throw limitError('已达游客上限，请登录解锁更多')
    }
    throw new Error(`API ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// ---------- 对外接口 ----------

// 创建雷达：自然语言 -> 后端 LLM 解析为结构化参数
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
      notify_channel: 'telegram',
      active: true,
      created_at: new Date().toISOString(),
    }
    MOCK_RADARS.unshift(radar)
    return radar
  }
  return request('/radars', {
    method: 'POST',
    body: JSON.stringify({ raw_query: rawQuery.trim() }),
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
      throw limitError('游客最多绑定 1 个渠道，登录解锁多渠道')
    }
    const c = MOCK_CHANNELS.find((x) => x.type === type)
    if (!c) throw new Error(`unknown channel: ${type}`)
    c.bound = true
    return { ...c }
  }
  return request(`/channels/${type}/bind`, {
    method: 'POST',
    body: JSON.stringify({ recipient: recipient || '' }),
  })
}
