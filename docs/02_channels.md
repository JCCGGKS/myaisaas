# 02 渠道接入与消息推送设计方案

> Watch Anything 的**渠道接入（绑定）与消息推送**设计方案。
> 最终渠道组合（已确认）：**`email` + `Web Push` + `飞书`**。`qq` 归并进 `email`，`微信` 降级为未来可选。
> 本期只做设计，不落地实现。

---

## 1. 范围与渠道组合（已确认）

| 渠道 | 角色 | 接入方式 | 验证方式 |
|---|---|---|---|
| `email` | 必到兜底（含 QQ 邮箱） | SMTP / 事务邮件 API | 一次性 token + 验证邮件 |
| `webpush` | 即时气泡（浏览器原生通知） | Push API + VAPID（自托管） | 浏览器订阅手势即所有权证明，立即 verified |
| `feishu` | 企业/团队向气泡（飞书） | 群机器人 Webhook（MVP） | 粘贴 webhook URL + 测试卡片连通即 verified |

- `qq` **不单列渠道**：用户填 QQ 号时自动识别并转 `{qq}@qq.com`，复用 `email` 机制。
- `微信`：本期不做（个人微信无官方直推 API，须企业微信中转 + 48h 窗口，集成成本高），列为未来可选。
- `webhook`（通用自定义）：本期不单列，但 `feishu` 的 MVP 形态本质就是飞书专属 webhook；通用 webhook 仍可作为未来高级渠道经 `ChannelFactory.register` 零改接入。

---

## 2. 各渠道机制

### 2.1 email（含 QQ 邮箱）
- 收件箱触达，最稳，零客户端依赖。
- 绑定：用户填地址（或 QQ 号）→ 发验证邮件 → 点链接确认。
- 发送：SMTP 或事务邮件 API（推荐后者，送达率高、省运维）。

### 2.2 webpush（浏览器通知）
- 用户授权后浏览器原生弹窗，关页面也能收，最贴近"雷达命中即时提醒"。
- **对游客零门槛**：订阅发生在页面内用户手势中，天然证明归属，无需绑定第三方账号。
- 机制：前端 `pushManager.subscribe({userVisibleOnly:true, applicationServerKey: VAPID_PUBLIC})` → 得到 `PushSubscription`（endpoint + 密钥）→ 提交后端存储；后端用 VAPID 私钥经 `pywebpush` 推送到 endpoint。
- 代价：需前端 Service Worker + 一对 VAPID 密钥；不同浏览器授权策略不一。

### 2.3 feishu（飞书，MVP = 群机器人 Webhook）
- 用户在飞书群添加「自定义机器人」得到 webhook URL，粘贴到绑定表单 → 我们 POST 消息卡片即达群。
- 绑定即验证：发送一张"绑定成功"测试卡片，连通即 `verified=True`。
- **增强（未来）**：飞书自建应用 + OAuth 授权获取 `open_id` + 应用消息卡片，实现**私信(DM)**推送；需创建企业应用、开权限、配事件回调，成本高于 Webhook。

---

## 3. 数据模型调整

`User.channel_bindings`（JSONB）每条结构：

```json
{
  "channel_type": "email | webpush | feishu",
  "recipient": "user@x.com | <PushSubscription JSON 字符串> | https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "verified": true,
  "bind_token": "email 验证用，一次性（webpush/feishu 无）",
  "bind_token_expire_at": "ISO | null",
  "verified_at": "ISO | null",
  "extra": "可选：feishu 是否为 DM 模式等"
}
```

- 渠道枚举：`["email", "webpush", "feishu"]`，替换原 `["telegram","email","webhook"]`。
- `Radar.notify_channels`（多通道列表）结构不变，值改新枚举。
- `webpush` 的 `recipient` 实为序列化后的 `PushSubscription`（endpoint+auth/key），发送时反序列化。

---

## 4. 绑定流程设计

### 4.1 email
```
POST /api/channels/email/bind  { recipient: "地址或QQ号" }
  → 规范化（qq 号补 @qq.com）
  → 生成一次性 bind_token（随机、30 分钟过期）
  → 写 channel_bindings（verified=false, bind_token 留存）
  → 发验证邮件（含 /api/channels/verify?token=xxx）
  → 返回 { bound:true, verified:false }

GET /api/channels/verify?token=xxx
  → 校验有效且未过期 → verified=true，清空 bind_token
```

### 4.2 webpush
```
前端：请求通知权限 → pushManager.subscribe(VAPID_PUBLIC) → 得到 subscription
POST /api/channels/webpush/bind  { subscription: {...} }
  → 订阅来自页面内用户手势，视为所有权证明 → verified=true 立即
  → 存储序列化 subscription 到 channel_bindings
```
- 重复 bind：更新 subscription（浏览器可能轮换 endpoint）。
- 游客同样可用（无需第三方账号）。

### 4.3 feishu
```
POST /api/channels/feishu/bind  { recipient: "webhook url" }
  → 发送"绑定成功"测试卡片到该 URL
  → 发送成功 → verified=true；失败 → 返回错误提示用户检查 URL
```

---

## 5. 推送实现设计

### 5.1 渠道策略（真实发送）
- `EmailChannel`：SMTP / 事务邮件 API（email 单发、HTML 格式）。
- `WebPushChannel`：`pywebpush` + VAPID 私钥 → 推到 endpoint，payload 为加密 JSON `{title, body, url}`。
- `FeishuChannel`：`POST` 消息卡片 JSON 到 webhook URL（MVP）；未来 DM 走应用消息 API。
- 保留 `FakeChannel` 供测试（不真发）。

### 5.2 消息格式（按渠道适配）
| 渠道 | 格式 |
|---|---|
| email | HTML 邮件：雷达名 + 标题 + 摘要 + 来源链接 |
| webpush | 标题 + 正文 + URL（点击打开雷达事件） |
| feishu | 消息卡片（card）：标题 + 摘要 + 链接按钮 |

`PushMessage(title, body, url)` 保持不变，各渠道自行格式化。

### 5.3 失败与重试
- `dispatch` 失败返回 `False` 不中断主流程（保留）。
- 单渠道失败按指数退避重试（如 3 次），全失败才记 `False` + ERROR 日志。
- Web Push 遇 `410 Gone`/`404`（订阅失效）→ 标记该 subscription 失效、不再重试、可从 bindings 移除。
- 重试仍失败 → 不写 `Notification`，下次扫描可再试。

---

## 6. 去重与防重发（修当前漏洞）

当前 `notify_radar` 不查 `Notification` 表、只累加 `event.pushed_channels`（内存态），监控循环重跑会**重复推**。修正：
1. 发送前先 `Notification.exists(event_id, channel)` 前置校验，已存在则跳过（权威去重在 DB）。
2. `event.pushed_channels`（JSON）作内存快查；`Notification` 表为持久化权威。
3. 多通道各自独立去重（同一事件在不同渠道各记一条）。

---

## 7. 安全与工程纪律

- **email 验证 token**：一次性、带过期，防冒用邮箱。
- **webpush**：VAPID 私钥仅服务端持有；subscription 按用户隔离存储；POST bind 补 CSRF `Origin` 校验。
- **feishu**：webhook URL 存库即视为可信接收端；URL 格式校验（仅限飞书域名）防误填/滥用。
- **CSRF（已实现）**：新增 `middleware/csrf.py` 的 `CSRFOriginMiddleware`，对写请求（POST/PUT/PATCH/DELETE）校验 `Origin` 与「本站 Host 源」或 `csrf_trusted_origins` 一致，不一致 403；安全方法跳过；缺 `Origin` 的写请求拒绝。`csrf_enabled` 可关闭（测试用），受信源 `csrf_trusted_origins` 生产需改为真实前端源。呼应 01_guest.md §8 第 1 步。
- **日志**（统一 `utils.logging`）：绑定、验证、发送起止/成败、重试、去重跳过，均打 INFO/ERROR，脱敏（不记 VAPID 私钥、subscription 明文可记但视为敏感、收件人隐私打码）。
- **测试**（遵循 AGENTS.md）：每渠道策略 + 绑定流程 + 去重 + 验签用 Fake/Mock 覆盖，不依赖真实邮件/飞书/浏览器跑通。

---

## 8. 待确认 / 待办

### 已拍板（2026-07-26）
- [x] **邮件发送选型（现阶段）= 本地 SMTP**：开发用 MailHog/Mailpit（localhost:1025，零成本零配置）。`EmailChannel` 底层抽象为可切换的 `EmailBackend`，后续无缝演进：个人 SMTP → 云厂 SMTP 中继 → 云厂 HTTP API。
- [x] **现阶段只落地 `email` 渠道**（本地 SMTP 真发 + 绑定验证 + 去重 + 重试）；`webpush` / `feishu` 留作后续扩展（本期绑定返回未实现）。

### 待确认（未来）
- [ ] 飞书是否仅做群机器人 Webhook（MVP），还是同期做应用消息 DM（需飞书自建应用 + OAuth）。
- [ ] VAPID 密钥如何生成与存储（环境变量 / KMS）（待 webpush 落地时定）。
- [ ] 生产切云厂邮件推送（阿里云/腾讯云）时的实名 + 发信域名(DKIM/SPF)配置。

### 本期设计交付
- [x] `docs/02_channels.md`（本文件，已按 email+webpush+feishu 定稿）
- [x] **email 渠道落地完成**：本地 SMTP 真发（MailHog 兼容）、绑定验证（一次性令牌 + 验证邮件）、`notify_radar` 去重前置校验、`dispatch` 指数退避重试。详见 `reports/2026-07-26_1700_渠道接入推送email落地.md`。
- [ ] `webpush` / `feishu`：尚未实现（绑定返回 501），留作后续扩展。

### 未来可选
- [ ] 微信（企业微信中转 / 微信客服，48h 窗口）
- [ ] 通用 webhook 高级渠道
- [ ] SMS 关键告警

### 关联的已记录待修项
- 旧 `notify_radar` 去重缺失（§6 覆盖）。
- 旧 telegram webhook 伪造 user_id 漏洞（本期渠道已无 telegram，自然消除）。
