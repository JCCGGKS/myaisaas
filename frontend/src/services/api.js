// API 服务层
// 真实后端就绪后，把 .env 的 VITE_USE_MOCK 改为 false 即可切到真实接口。
// 接口约定见 AGENTS.md 的「关键 API」章节。

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') === 'true'

const delay = (ms) => new Promise((r) => setTimeout(r, ms))
const uid = () =>
  (crypto.randomUUID && crypto.randomUUID()) ||
  `r_${Date.now()}_${Math.random().toString(36).slice(2)}`

// ---------- mock 数据（无后端时演示用） ----------
const MOCK_RADARS = [
  {
    id: uid(),
    raw_query: 'Monitor LISA — 演唱会 & 新歌',
    keywords: ['LISA', 'BLACKPINK', 'YG'],
    sources: ['official_site', 'twitter', 'news'],
    notify_channel: 'telegram',
    active: true,
    created_at: new Date(Date.now() - 3600_000).toISOString(),
  },
  {
    id: uid(),
    raw_query: 'OpenAI 与 AI Agent 行业动态',
    keywords: ['OpenAI', 'Agent', 'LLM'],
    sources: ['news', 'blog'],
    notify_channel: 'telegram',
    active: true,
    created_at: new Date(Date.now() - 7200_000).toISOString(),
  },
]

const MOCK_EVENTS = {
  [MOCK_RADARS[0].id]: [
    {
      id: uid(),
      radar_id: MOCK_RADARS[0].id,
      title: 'Lisa 确认加盟科切拉音乐节，4 月登台',
      source_url: 'https://example.com/lisa-coachella',
      relevance_score: 0.94,
      summarized: true,
      created_at: new Date(Date.now() - 120_000).toISOString(),
    },
    {
      id: uid(),
      radar_id: MOCK_RADARS[0].id,
      title: 'LISA 个人纪录片预告片上线',
      source_url: 'https://example.com/lisa-doc',
      relevance_score: 0.81,
      summarized: true,
      created_at: new Date(Date.now() - 1080_000).toISOString(),
    },
  ],
  [MOCK_RADARS[1].id]: [
    {
      id: uid(),
      radar_id: MOCK_RADARS[1].id,
      title: 'OpenAI 发布新 Agent SDK，支持长任务编排',
      source_url: 'https://example.com/openai-agent',
      relevance_score: 0.9,
      summarized: true,
      created_at: new Date(Date.now() - 2460_000).toISOString(),
    },
  ],
}

// ---------- 真实请求封装 ----------
async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}`)
  return res.json()
}

// ---------- 对外接口 ----------

// 创建雷达：自然语言 -> 后端 LLM 解析为结构化参数
export async function createRadar(rawQuery) {
  if (!rawQuery || !rawQuery.trim()) throw new Error('监控目标不能为空')
  if (USE_MOCK) {
    await delay(600)
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
