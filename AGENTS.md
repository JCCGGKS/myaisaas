# AGENTS.md — Watch Anything (AI 监测雷达 SaaS)

本文件记录项目的产品定位、技术栈、关键架构约定与**协作/工程纪律**，供后续开发与 AI 协作参考。Agent 在本仓库工作时，除遵循架构设计外，还须遵守文末「工程纪律」章节。

> 本仓库**使用中文**沟通与编写文档。

## 项目定位

**Watch Anything** —— 一个 AI 监测雷达 SaaS。用户用自然语言告诉系统"想盯住什么"，系统**持续监测**相关信息源，发现重要变化时**主动推送给用户**（而非被动等用户来查）。

> **核心语义**：雷达 = 设定目标 → 持续扫描 → 命中即报告。
> 它不是"定时跑批报表"，而是**常驻监测循环 + 告警分发系统**。
> 技术上靠短轮询或事件源（RSS/Webhook/流）实现"持续"的体感；产品本质是**主动报告**。

## 技术栈

### 前端
- Vue 3 + Vite（沿用现有 `frontend/`）
- 组件：导航 / Hero 输入 / 工作原理 / 示例 / CTA / 页脚
- 后续新增 `/dashboard` 展示雷达列表与事件流

### 后端
- Python + FastAPI（异步友好、AI/LLM 生态成熟）
- SQLAlchemy + Alembic（ORM 与迁移）

### 数据与基础设施
- PostgreSQL（Docker Compose 一键起）
- 关键能力：
  - `pgvector`：语义检索 / 事件去重 / 聚类
  - `JSONB`：Radar 灵活配置（sources / keywords / notify_config）
- Redis：任务队列 broker + 去重 / 限流缓存

### 异步与任务
- Celery + Redis：常驻监控循环、增量爬取、LLM 过滤、告警分发
- 频率与实时解耦：优先用数据源 push（RSS/Webhook/流）；不支持的用短间隔轮询

### AI / LLM
- OpenAI 兼容接口（可切换 Claude / 国产模型）
- 用途：自然语言 → 结构化雷达参数、相关性/重要性打分、事件摘要

## 核心数据模型（摘要）

- **User**：身份标识、`is_guest` 游客标记、通用渠道绑定 `channel_bindings`（JSONB：`[{channel_type, recipient, verified}]`，替代单一 `telegram_chat_id`）、通知偏好
- **Radar**：监控目标 = 原始描述 + 结构化参数（keywords / sources / 过滤规则 / 通知通道）；有状态、增量盯防；`owner_id` 关联 User
- **Event**：命中的候选事件（标题、来源、相关性分、摘要、是否推送）
- **Notification**：已推送记录，防重发

## 关键 API

| 接口 | 说明 |
|---|---|
| `POST /api/radars` | 创建雷达（自然语言 → LLM 解析）；游客超限额返回 `limit_exceeded` |
| `GET /api/radars` | 我的雷达列表（按当前用户/游客隔离） |
| `GET /api/radars/:id/events` | 雷达事件流 |
| `GET /api/channels` | 列出可用渠道 + 已绑定状态 |
| `POST /api/channels/{type}/bind` | 绑定渠道：email/webhook 直接提交；telegram 返回 `connect_url` |
| `POST /api/auth/register` | 注册（游客达限额后触发） |
| `POST /api/auth/login` | 登录 |
| `POST /api/auth/merge-guest` | 登录后合并游客数据到账号 |
| `POST /webhooks/telegram` | Bot 回调，写入 `chat_id` |

## 后端项目结构

后端代码统一放在 `src/` 下，采用分层架构：

```
src/
├── api/          # 路由/接口层（HTTP 入口），只做校验 + 调 business
├── business/     # 业务逻辑层（服务层），核心流程编排 + 通知子系统
├── config/       # 配置层（pydantic-settings；读取 etc/settings.{env}.yml）
├── dao/          # 数据访问层（SQLAlchemy CRUD，屏蔽 ORM 细节）
├── data/         # 数据基础设施层（engine/session 初始化 + seed/迁移）
├── model/        # ORM 模型层（SQLAlchemy 表定义 + Base）
├── schema/       # 接口契约层（Pydantic request/response DTO）
├── middleware/   # 中间件层（CORS / 日志 / 鉴权 / 统一异常）
├── pkgs/         # 外部依赖封装包（LLM / Telegram / Redis 等第三方客户端）
└── utils/        # 通用工具层（ID / 时间 / HTTP / 日志 / 异常）
```

### 各模块职责

| 模块 | 职责 | 本项目落点 |
|---|---|---|
| **api** | 路由/接口层 | `/api/radars`、`/api/radars/:id/events`、`/api/channels`、`/api/auth/*`、`/webhooks/telegram`；只校验参数 + 调 business |
| **business** | 业务逻辑层 | 创建雷达时 LLM 解析自然语言 → 结构化参数、监控循环编排、事件相关性过滤、通知分发；**通知子系统**（`ChannelFactory` + 各渠道策略）放在 `business/notifier/` |
| **config** | 配置层 | DB URL、JWT/密钥、LLM key、Telegram token、Redis 地址；从 `etc/settings.{env}.yml` 按 `APP_ENV` 加载，嵌套 struct 管理 |
| **dao** | 数据访问层 | Radar/Event/Notification 的写与查，对 business 屏蔽 ORM |
| **model** | ORM 模型层 | `User` / `Radar` / `Event` / `Notification` 表定义 + `Base` |
| **schema** | 接口契约层 | 创建雷达入参、事件出参等 Pydantic DTO |
| **middleware** | 中间件层 | CORS、请求日志、鉴权（JWT/API Key）、统一异常 |
| **pkgs** | 外部依赖封装包 | LLM 客户端（OpenAI 兼容）、Telegram Bot 客户端、Redis 客户端等第三方 SDK 封装 |
| **data** | 数据基础设施层 | DB engine / sessionmaker 初始化、连接管理；种子/初始化数据、Alembic 迁移 |
| **utils** | 通用工具层 | ID 生成、时间格式化、HTTP 包装、日志初始化、自定义异常 |

> 设计要点：依赖方向 `api → business → dao → model`，配置/工具由 `config`/`utils` 横向提供；`pkgs` 封装一切外部不确定依赖，便于替换与测试。

## 配置管理约定（etc/ 按环境分文件 + 嵌套 struct）

> 所有相关配置集中在仓库根的 `etc/` 目录（与 `src/` 同层级）。采用**按环境分文件 + 嵌套 struct** 方式管理。

- **目录与文件**：`etc/` 下每个环境一个文件，命名 `settings.{env}.yml`
  （当前：`settings.local.yml` / `settings.test.yml` / `settings.prod.yml`）。
- **环境选择**：由**进程环境变量 `APP_ENV`**（`local` / `test` / `prod`）决定加载哪个文件；
  **未设置 `APP_ENV` 时默认读取 `local`**。`src/config/settings.py` 据此拼出
  `etc/settings.{APP_ENV}.yml` 并加载（启动时有 `INFO 配置环境 APP_ENV=...` 日志）。
- **示例模板**：`etc/settings.local.example.yml` 是带占位值与注释的示例，
  复制为 `etc/settings.local.yml` 后按需修改即可，不把真实密钥提交进仓库。
- **嵌套 struct（结构嵌入）**：配置按「域」分组，相同类别归入同一个结构下；
  每个域对应 `src/config/settings.py` 里的一个 pydantic 子模型（struct），如
  `database` / `guest` / `app` / `auth` / `csrf` / `email` / `telegram` / `llm` / `monitor` / `source` / `log`。
  代码以结构化方式读取，如 `settings.email.smtp_host`、`settings.monitor.relevance_threshold`。
- **覆盖优先级**：环境变量 `WA_*`  >  `etc/settings.{env}.yml`  >  `Settings` 类默认值。
  - 嵌套字段用**双下划线**分隔：`WA_EMAIL__SMTP_HOST`、`WA_LLM__API_KEY`、
    `WA_AUTH__SECRET_KEY`、`WA_DATABASE__URL` 等。
  - `APP_ENV` 本身是**普通进程环境变量**（非 `WA_` 前缀），在 shell / 容器 `environment` 中设置。

## 通知子系统设计（策略模式 + 工厂模式）

消息推送渠道采用 **策略模式 + 工厂模式** 解耦，新增渠道不动分发逻辑。

### 策略接口（Strategy）
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PushMessage:
    title: str
    body: str
    url: str | None = None

class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, recipient: str, msg: PushMessage) -> bool:
        """recipient 由各渠道解释：telegram=chat_id, email=address, webhook=url"""
        ...
```

### 具体策略（Concrete Strategies）
```python
class TelegramChannel(NotificationChannel):
    def __init__(self, token: str): ...
    async def send(self, chat_id: str, msg: PushMessage) -> bool: ...

class EmailChannel(NotificationChannel):
    async def send(self, address: str, msg: PushMessage) -> bool: ...

class FeishuChannel(NotificationChannel):
    # 飞书群机器人：recipient=webhook URL，构造 interactive 卡片 POST；
    # 机器人开启签名校验时由 settings.feishu.sign_secret 提供密钥。
    async def send(self, webhook_url: str, msg: PushMessage) -> bool: ...

class WebhookChannel(NotificationChannel):
    async def send(self, url: str, msg: PushMessage) -> bool: ...
```

### 工厂（Factory）
```python
class ChannelFactory:
    _registry = {
        "telegram": TelegramChannel,
        "email": EmailChannel,
        "feishu": FeishuChannel,
        "webhook": WebhookChannel,
        "webpush": WebpushChannel,
    }

    @classmethod
    def create(cls, channel_type: str, **config) -> NotificationChannel:
        if channel_type not in cls._registry:
            raise ValueError(f"unknown channel: {channel_type}")
        return cls._registry[channel_type](**config)

    @classmethod
    def register(cls, name: str, klass: type) -> None:
        cls._registry[name] = klass   # 扩展点：新增渠道只注册，不改分发代码
```

### Worker 分发（与雷达解耦）
```python
async def dispatch(radar: Radar, event: Event):
    channel = ChannelFactory.create(radar.notify_channel, **settings)
    ok = await channel.send(radar.user.recipient, PushMessage(...))
    if ok:
        record_notification(event.id, radar.notify_channel)  # 防重发
```
- `radar.notify_channel` 存**字符串类型**（`"telegram"` / `"email"` …），工厂据此实例化。
- 多通道支持：将字段改为 list，工厂循环创建即可。

### 设计约束
- **开闭原则**：加渠道 = 新策略类 + `register`，分管发代码零改动。
- **可测试**：单测可注入 `FakeChannel`，不真发消息。
- **配置驱动**：渠道类型存库（`JSONB` 的 `notify_config`），运行时由工厂实例化，无需改代码即可切换。
- **推送优先**：Telegram 为主通道（还原原型气泡效果），Dashboard 事件流作为辅助回溯。

## 游客模式与渠道绑定（限额设计）

### 游客优先体验
- 进入即**游客**：用设备/cookie 生成 `User(is_guest=true)`，无需登录即可体验完整"创建雷达 + 绑定渠道"流程。
- 游客数据在登录/注册后通过 `POST /api/auth/merge-guest` 合并到账号。

### 限额（MVP）
| 角色 | 雷达数 | 绑定渠道数 |
|---|---|---|
| 游客 | ≤ 1 | ≤ 1 |
| 登录用户 | 不限制（后续按套餐） | 可同时绑定多个渠道 |

- 超出限额时，`POST /api/radars` 与 `POST /api/channels/{type}/bind` 返回 `limit_exceeded`（HTTP 402）。
- 前端捕获该状态 → 弹出登录/注册框，完成后继续原操作。

### 渠道绑定（渠道无关，不写死 telegram）
- `GET /api/channels` 返回可用渠道类型与每个渠道的绑定状态。
- `POST /api/channels/{type}/bind`：
  - `email` / `webhook`：直接提交 `recipient`（`address` / `url`）即绑定。
  - `telegram`：提交后返回 `connect_url`，用户打开与 bot 对话，`POST /webhooks/telegram` 回调写入 `chat_id`。
- `notify_channel` 存字符串；多通道时升级为 list，分发时工厂循环创建。

## 设计原则小结

1. 产品是**主动报告**，不是批处理报表 —— 通知是一等公民。
2. 雷达**有状态、增量盯防**，每次只报新增/变化（dedup + 增量）。
3. 智能过滤是核心：LLM 相关性/重要性打分，过阈值才报告，避免骚扰。
4. 推送渠道**策略 + 工厂**，可插拔、可测试、配置驱动。

## 工程纪律（Agent 必须遵守）

以下约定用于保证代码可维护、问题可追踪。Agent 每完成改动都应自检是否达标。

### 1. 每完成一个新的独立模块，必须进行相应测试
- 任何新增的独立模块（如 `business/notifier/` 各渠道、`dao/` 的某张表访问、`pkgs/` 的客户端封装）都**配套编写测试**，不达标视为未完工。
- 测试位置：与模块同层的 `tests/`（如 `src/business/notifier/tests/`），或仓库根 `tests/`，遵循 `test_<模块>_<场景>.py` 命名。
- 测试应覆盖：正常路径 + 边界/异常路径。
- 外部依赖（LLM、Telegram、Redis、DB）通过**注入 Fake / Mock** 隔离，不依赖真实服务即可跑通（如通知子系统可注入 `FakeChannel` 验证分发逻辑）。
- 跑测试是模块"完成"的验收门槛，而不是可选步骤。

### 2. 在必要的位置打印日志
- 日志统一经 `utils/` 的日志初始化模块获取 logger，**禁止**散用 `print` 做业务日志。
- 必须打日志的位置：
  - **入口/边界**：API 请求进入与返回、Webhook 回调接收；
  - **关键流程节点**：雷达创建（含 LLM 解析结果）、一次监测扫描的开始/结束、事件命中与相关性打分、通知分发（渠道、接收人、成功/失败）；
  - **异常与失败**：外部调用失败（LLM/Telegram/Redis）、DB 写入异常，需打印错误与上下文，便于排查；
  - **外部依赖交互**：调用 LLM、发推送、读写缓存时记录耗时与结果摘要。
- 日志级别：`DEBUG` 记细节、`INFO` 记关键步骤、`WARNING/ERROR` 记异常；不打敏感信息（密钥、token 明文、用户隐私）。
- 原则：**出问题时能靠日志还原链路**，但不要刷屏（高频轮询内的逐条日志用 `DEBUG`）。

### 3. 每次任务完成必须产出结论并写入 reports/
- 每完成一个任务/一轮改动，Agent 须向用户产出结构化结论，并写入仓库 `reports/` 目录下、以日期时间命名的文件（如 `reports/2026-07-26_1430_xxx.md`）：
  1. **完成了什么**：本次实际落地的内容（改动点 / 验证结果）。
  2. **需要确认的**：需要用户拍板、或存在歧义/风险、或未能自动验证的部分。
  3. **待完成的**：尚未做、依赖上游、或下一步建议。
- 结论须用中文、简洁、面向"用户能否据此判断进度"。
- 文件名必须带日期与时间，便于追溯；不写入 AGENTS.md。
