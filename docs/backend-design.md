# Watch Anything 后端技术方案设计（第一版 / v1）

> 本文基于 `AGENTS.md`（产品定位 + 分层架构 + 通知子系统 + 游客限额）与现有 `src/` 代码现状撰写。
> 目标：把当前"骨架"补全为**可运行的 v1 后端**——自然语言建雷达 → 持续监控 → LLM 相关性过滤 → 命中主动推送。
> 约定：全文中文；遵循 AGENTS.md「工程纪律」（每模块测试、统一日志）。

---

## 1. 目标与范围

### 1.1 v1 要补齐的能力（现有代码缺口）
| 能力 | 现状 | v1 目标 |
|---|---|---|
| 雷达创建 | 仅存 `raw_query`，结构化参数留空 | 创建时 LLM 解析自然语言 → `keywords/sources/filters` |
| 事件来源 | 无（mock 才有事件） | 监控循环从数据源拉取/接收真实候选事件 |
| 相关性过滤 | 无 | LLM 打分 + 阈值，低于丢弃、高于留存 |
| 事件去重 | 无 | `dedup_key` 去重 + 增量游标，避免重复推送 |
| 通知分发 | 策略+工厂已就绪，但无调用方 | 扫描命中后多通道分发 + `Notification` 防重发 |
| 调度 | 无 | 调度器周期触发扫描（push 源即时、pull 源短轮询） |
| 游客闭环 | 已就绪（限额/登录合并） | 保持不变，仅适配多通道数据模型 |

### 1.2 不在 v1（明确划界，避免过度设计）
- 复杂事件聚类 / 时间序列分析
- 多租户计费、套餐系统
- 全量第三方 API 深度接入（v1 用 MVP 连接器 + 可插拔接口，真实 API 留 stub）

---

## 2. 架构与分层（沿用 AGENTS.md）

依赖方向保持 `api → business → dao → model`，配置/工具由 `config`/`utils` 横向提供；`pkgs` 封装一切外部不确定依赖（LLM、Telegram、SMTP、RSS/HTTP 客户端）。

**新增监控子系统**归属 `business/monitor/`，不污染现有 `business/`：
```
src/business/monitor/
├── scheduler.py        # 调度入口（决定何时扫哪些雷达）
├── scanner.py          # 扫描编排：取雷达 → 拉源 → 打分 → 去重 → 落库 → 分发
├── scorer.py           # LLM 相关性/重要性打分 + 摘要（调 pkgs/llm）
├── dedup.py            # 基于 dedup_key 的去重
└── sources/            # 数据源连接器（开闭原则）
    ├── base.py         # Source 接口：fetch(state) -> list[RawItem]
    ├── rss.py
    ├── web.py          # 网页/搜索抓取（httpx + 简易解析）
    └── webhook.py      # 接收 /api/ingest 推送进来的原始条目
```

---

## 3. 数据模型设计

### 3.1 变更总览
| 模型 | 当前 | v1 变更 |
|---|---|---|
| `User` | `channel_bindings` JSON | **不变**（账户级渠道 `{channel_type, recipient, verified}`） |
| `Radar` | `notify_channel` 单值 `String(32)` | 改为 **`notify_channels` JSON(list[str])**；新增 `scan_state` JSON、`last_scan_at`、`status`、`last_error` |
| `Event` | `title/url/score/summary/pushed` | 新增 `dedup_key`(String, **radar 内唯一**)、`pushed_channels` JSON、可选 `is_read` |
| `Notification` | `event_id/channel/recipient` | **不变** |

> **为何 `notify_channel` 要变 list**：前端已改为每个雷达可绑多个渠道（`radarChannels(r)` 优先读 `channels` 数组）。后端需相应支持多通道，dispatch 时循环创建。AGENTS.md 已规划"将字段改为 list，工厂循环创建即可"。

> **Source 是否独立成表**：v1 不拆表，数据源配置内联在 `radar.sources`(JSON) + 增量游标放 `radar.scan_state`(JSON)，避免过早抽象；后续若需共享源/授权再拆 `Source` 表。

### 3.2 `Radar` 字段（v1）
```python
class Radar(Base):
    id
    owner_id              # FK User
    raw_query             # 用户原始自然语言（不变）
    keywords = JSON       # LLM 解析结果（v1 填充）
    sources  = JSON       # 数据源列表，如 [{"type":"rss","url":"..."}]
    filters  = JSON       # 过滤规则（语言/地域/排除词等）
    notify_channels = JSON(default=list)   # v1：多通道，如 ["telegram","email"]
    scan_state = JSON(default=dict)        # 增量游标：{ "rss:<url>": "last_guid/last_ts", ... }
    status = String(default="active")      # active / paused / error
    last_scan_at = DateTime(nullable)
    last_error = Text(nullable)
    active = Boolean(default=True)          # 业务启用开关（与 status 解耦：paused 仍 active=True）
    created_at
```
> 迁移时把旧 `notify_channel`（非空字符串）写入 `notify_channels=[旧值]`。

### 3.3 `Event` 字段（v1 增量）
```python
class Event(Base):
    id
    radar_id
    dedup_key = String(128)   # 唯一约束(radar_id, dedup_key)：来源归一化后的指纹
    title
    source_url
    relevance_score = Float
    summary = Text
    pushed = DateTime(nullable)        # 首次推送时间
    pushed_channels = JSON(default=list)  # 已推送到的渠道，防重发
    is_read = Boolean(default=False)  # 前端已读状态（可选，v1 可后置）
    created_at
```

### 3.4 迁移方式
- 引入 **Alembic**（AGENTS.md 已规划 `src/data` 放迁移）。提供初始 migration：
  1. `radars`：新增 `notify_channels`/`scan_state`/`last_scan_at`/`status`/`last_error`；旧 `notify_channel` 数据迁移进 `notify_channels`。
  2. `events`：新增 `dedup_key`（建唯一索引）、`pushed_channels`、`is_read`。
- 开发期仍可用 `init_db()`(create_all) 快速迭代；**生产环境走 Alembic**，禁止 create_all 覆盖。

---

## 4. 接口设计（API）

### 4.1 保留现有接口
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/radars` | 创建雷达（v1 增加 LLM 解析） |
| GET | `/api/radars` | 我的雷达列表 |
| GET | `/api/radars/{id}/events` | 雷达事件流（v1 加分页/过滤） |
| GET | `/api/channels` | 可用渠道 + 绑定状态 |
| POST | `/api/channels/{type}/bind` | 绑定账户渠道（telegram 返回 connect_url） |
| POST | `/api/auth/register` `/login` `/merge-guest` | 游客升级 |
| POST | `/webhooks/telegram` | bot 回填 chat_id |
| GET | `/healthz` | 健康检查 |

### 4.2 v1 新增 / 调整接口
| 方法 | 路径 | 说明 |
|---|---|---|
| **POST** | `/api/radars` | 入参 `notify_channels: list[str]=[]`（替代原单值 `notify_channel`）；响应带回 LLM 解析的 `keywords/sources/filters` |
| GET | `/api/radars/{id}` | 单雷达详情（含 `notify_channels`、`status`、`last_scan_at`、最近事件） |
| POST | `/api/radars/{id}/pause` `/resume` | 暂停/恢复该雷达监控（改 `status`；`active` 不变） |
| PUT | `/api/radars/{id}/channels` | 设置该雷达的多通道列表（覆盖/合并）；校验均为账户已绑渠道 |
| POST | `/api/radars/{id}/sources` | 手动追加数据源（可选，v1 也可创建时一并传 `sources`） |
| GET | `/api/radars/{id}/events` | 新增 `?since=&unread=&limit=` 分页/过滤 |
| POST | `/api/ingest/{source_type}` | 接收 push 源（webhook/RSS 回调）写入候选原始条目，进入打分→去重→推送流程 |

**关键入参/响应示例**
```jsonc
// POST /api/radars
{ "raw_query": "LISA 演唱会与新歌动态", "notify_channels": ["telegram"] }
→ 201 {
  "id": 12,
  "raw_query": "LISA 演唱会与新歌动态",
  "keywords": ["LISA","演唱会","新歌"],
  "sources": [{"type":"web","query":"LISA 演唱会"}],
  "filters": {"lang":"zh"},
  "notify_channels": ["telegram"],
  "status": "active",
  "created_at": "2026-07-26T..."
}

// PUT /api/radars/12/channels
{ "notify_channels": ["telegram","email"] } → 200 { ... "notify_channels": ["telegram","email"] }
```

### 4.3 DTO 调整（`schema/dtos.py`）
- `RadarCreate.notify_channel: str` → `notify_channels: list[str] = []`
- `RadarOut` 增加 `notify_channels`、`status`、`last_scan_at`、`keywords/sources/filters`（已部分有）
- 新增 `RadarChannelsIn`、`RadarStatusIn`、`EventQuery`(since/unread/limit)

---

## 5. 关键流程

### 5.1 创建雷达（含 LLM 解析）
```
api(POST /api/radars)
 → radar_service.create(raw_query, notify_channels)
   → LLMParser.parse(raw_query)        # pkgs/llm：自然语言 → {keywords, sources list, filters}
   → radar_dao.create(..., keywords, sources, filters, notify_channels)
   → 返回 RadarOut（含解析结果）
```
- **降级**：LLM 不可用时，用关键词抽取兜底（raw_query 分词），监控仍可进行；记 WARNING 日志。

### 5.2 监控扫描循环（核心）
```
scheduler（周期 / 事件触发）
 → 取 status=active 的雷达
 → 对每个 radar：
     scanner.scan(radar):
       1. 取 radar.sources + radar.scan_state（增量游标）
       2. 对每个 source：fetch(state) → list[RawItem]   # sources/* 各实现
       3. 逐条 item：
            - 生成 dedup_key（radar_id + 来源归一化指纹）
            - dedup 命中 → 跳过
            - scorer.score(item, radar) → 相关性/重要性分 + 摘要
            - 分 < 阈值 → 丢弃（记 DEBUG）
            - 分 ≥ 阈值 → event_dao.create(Event)
       4. 高分事件 → notifier 多通道分发（见 5.4）
       5. 更新 radar.scan_state（游标）/ last_scan_at
```
- 单条失败（某源挂了）不影响其他源/雷达；异常写 `last_error=status=error`（可手动 resume）。

### 5.3 频率与实时解耦（AGENTS.md 核心语义）
- **push 源**（webhook、RSS 有更新推送）：通过 `/api/ingest/{type}` 即时进入 5.2 流程，体感"实时"。
- **pull 源**（网页/搜索）：调度器短间隔轮询 + `scan_state` 游标增量，避免重复。
- 统一以 `scan_state` 记录 `last_seen`，"持续"体感由轮询/推送共同构成，而非定时批报表。

### 5.4 通知分发（多通道 + 防重发）
```
for ch in radar.notify_channels:
    recipient = user.channel_bindings 中匹配 ch 的 recipient
    ok = await dispatch(ch, recipient, PushMessage(title, body, url))
    if ok: notification_dao.record(event.id, ch, recipient)  # 防重发
```
- 复用现有 `notifier/`（策略+工厂）；`dispatch` 已具备异常兜底（失败返回 False，不中断主流程）。

---

## 6. LLM 集成（`pkgs/llm`）

- 封装 OpenAI 兼容接口（可切 Claude / 国产模型）：
  - `parse_query(text) -> {keywords, sources, filters}`（json mode / function calling）
  - `score(item, radar) -> {relevance, summary}`
- **成本/稳定性**：
  - 超时与降级：打分失败 → 关键词匹配兜底；解析失败 → 分词兜底。
  - 可缓存重复查询的解析结果。
- **配置**（`config/settings.py` 新增）：`llm_base_url`、`llm_api_key`、`llm_model`、`llm_timeout`、`relevance_threshold`。

---

## 7. 数据源连接器（`business/monitor/sources/`）

- `base.Source`：`async def fetch(state: dict) -> list[RawItem]`；`RawItem` 含 `raw_title/url/content`。
- 各实现：
  - `RSSSource`：拉 RSS/Atom，用 `state` 记 `last_guid/last_ts` 增量。
  - `WebSource`：httpx 抓取 + 简易正文解析（标题/链接抽取），按关键词/时间过滤。
  - `WebhookSource`：不主动 fetch，由 `/api/ingest` 把外部推送转成 `RawItem` 入队。
- **开闭原则**：加新源 = 新类 + 注册，不动 `scanner` 编排。
- v1 优先级：RSS（最稳）→ Web → Webhook 接收。

---

## 8. 调度与运行

两种选项：
- **A. Celery + Redis**（AGENTS.md 规划）：beat 周期触发 `scan_all`，worker 执行。生产友好、可水平扩展。
- **B. 轻量 asyncio 调度**（apscheduler 或自写 loop）：单进程零额外依赖，MVP 最快跑通闭环。

**v1 推荐：先 B 跑通闭环**（开发/演示单进程即可），抽象出 `scheduler.trigger_scan(radar_id)` 接口；生产再切 A，仅需替换调度入口，扫描/打分/分发逻辑不变。

---

## 9. 工程纪律（遵循 AGENTS.md）

- **每模块测试**：`business/monitor/`、`business/monitor/sources/`、`pkgs/llm` 均配套测试；用 **FakeLLM / FakeSource / FakeChannel** 注入，不依赖真实外部服务。
- **日志**：统一经 `utils/logging`；扫描开始/结束、事件命中、打分、分发成功/失败、外部调用耗时均打日志；高频轮询内逐条用 DEBUG。
- **现有测试保留**：游客限额、登录合并、notifier 在模型变更后需适配（`notify_channel`→`notify_channels`）。

---

## 10. 分阶段实施计划（v1 落地）

| Phase | 内容 | 验收 |
|---|---|---|
| **P0** | 数据模型迁移：多通道 + scan_state + dedup_key；Alembic 迁移脚本；DTO/DAO 适配；现有测试适配 | 测试通过；旧 `notify_channel` 数据迁进 `notify_channels` |
| **P1** | `pkgs/llm` 封装 + LLM 解析接入创建雷达（含降级）；`RadarCreate`/`RadarOut` 改多通道 | 创建雷达返回结构化参数；LLM 挂时降级不崩 |
| **P2** | `business/monitor/sources/`（RSS/Web）+ `scanner` 扫描编排 + 增量游标 | FakeSource 驱动下，扫描能把原始条目变成候选 |
| **P3** | `scorer`（LLM 打分/摘要）+ `dedup`（dedup_key 去重）+ Event 落库 | 低于阈值丢弃、高于阈值留存；重复源不重复落库 |
| **P4** | 多通道分发 + `Notification` 防重发 + 控制接口（pause/resume/channels）+ `/api/ingest` | 命中事件推到多个渠道；记录防重发；可暂停/恢复 |
| **P5** | 真实后端接通前端（`VITE_USE_MOCK=false`）+ 联调 + 测试补全 | 浏览器走通：建雷达→监控→事件流→推送 |

每 Phase 可独立交付、独立测试。

---

## 11. 待确认决策点
1. **调度方案**：v1 先用轻量 asyncio 调度（B），还是直接上 Celery+Redis（A）？
2. **账户绑渠道 vs 雷达渠道关系**：v1 采用"账户绑定渠道后自动追加到所有雷达 `notify_channels`（去重），并允许 `PUT` 单独管理每雷达"——是否认可？
3. **阈值与打分**：默认 `relevance_threshold` 取多少（建议 0.6）？是否需要用户可调？

> 以上确认后即可从 **P0** 开始实施。
