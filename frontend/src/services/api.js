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

// 灌入示例事件（演示用）：用雷达自身关键词构造命中率=1.0 的条目，确保过阈值被保留。
// 走真实 /api/ingest/webhook，触发打分→去重→落库→推送完整链路。
export async function seedDemoEvents(radarId, keywords = []) {
  const kws = Array.isArray(keywords) ? keywords : []
  const base = kws.length ? kws.join(' ') : '相关动态'
  const items = [
    { title: `${base}：官方公布最新进展`, url: 'https://example.com/demo-1', content: `${base} 的示例内容，用于演示事件流。` },
    { title: `${base}：行业媒体跟进报道`, url: 'https://example.com/demo-2', content: `${base} 的示例内容，用于演示事件流。` },
  ]
  if (USE_MOCK) {
    await delay(300)
    const evs = (MOCK_EVENTS[radarId] ||= [])
    items.forEach((it, i) => {
      evs.push({
        id: uid(),
        radar_id: radarId,
        title: it.title,
        source_url: it.url,
        relevance_score: 0.95 - i * 0.1,
        summary: true,
        created_at: new Date().toISOString(),
      })
    })
    return { ok: true, processed: items.length }
  }
  return request('/ingest/webhook', {
    method: 'POST',
    body: JSON.stringify({ radar_id: radarId, items }),
  })
}
