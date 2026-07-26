# 01 鉴权与游客模式方案

> 本文档记录 Watch Anything 的鉴权设计决策：**JWT 存 httponly cookie、与游客标识分桶存储**，以及为什么这样选。
> 适用场景：浏览器优先的 SaaS，且必须支持「游客免登录体验」。

---

## 1. 核心结论

- **JWT 放在 httponly cookie，不放在 `Authorization` header。**
- **JWT（登录态）与游客标识（匿名 ID）用两个独立 cookie，绝不混装。**
- 解析优先级：先认 `wa_auth`（JWT）→ 无效即「未登录」，**不降级成游客** → 再读 `wa_guest`（匿名 ID）。
- 只有在「对外暴露公开 API / 移动端 / 第三方调用」时才**额外**支持 `Authorization: Bearer`，即双通道并行。

---

## 2. 为什么 JWT 放 cookie 而不是 Authorization header

本项目是浏览器 SaaS，且强依赖游客模式，cookie 方案在安全与工程成本上更平衡：
+ XSS 跨站脚本攻击 Cross-Site Scripting
+ CSRF 跨站请求伪造 Cross-Site Request Forgery

| 维度 | httponly cookie（采用） | Authorization header |
|---|---|---|
| 防 XSS | ✅ JS 读不到 token，偷不走 | ❌ 必落 localStorage/JS 内存，XSS 易失 |
| 前端成本 | ✅ 自动携带，游客体系零改动 | ❌ 每次请求手动塞 header、刷新/重发都要管 |
| CSRF | ⚠️ 有，靠 `SameSite`/CSRF token 补 | ✅ 自定义头自带 CORS 预检保护 |
| 非浏览器客户端 | ⚠️ 需支持 cookie jar | ✅ curl/App 更自然 |
| 登出/过期 | 清 cookie 即可 | 前端删 token 即可 |

**关键判断**：对本项目而言，XSS 是首要矛盾（token 必然在浏览器存活），httponly cookie 从根本上消除「JS 偷 token」；CSRF 的代价可用 `SameSite=Strict/Lax` + 必要时的 CSRF token 兜住。

---

## 3. 为什么不把 JWT 和游客标识放同一个 cookie

原实现用单一 cookie `wa_uid` 既装 JWT 又装 `dev_xxx`，靠 `verify_token` 失败来「猜」是不是游客。隐患：

1. **伪造即游客**：任何乱填字符串进该 cookie → `verify_token` 失败 → 被当 `device_id` → `upsert_guest` 直接建/取游客账号。攻击者可凭空生成游客身份。
2. **高/低价值凭证共用作用域**：JWT（高价值）与游客标识（低价值）无法分别设 `SameSite`/过期策略。
3. **隐式约定易歧义**：解析靠「失败即游客」，逻辑不显式。

参考 Curity OAuth cookie 最佳实践：**不同 token 类型必须用独立 cookie，并分别收紧 `Domain`/`Path`/`SameSite`**；token 永不进 `localStorage`。

---

## 4. 采用的设计：双 cookie 分桶

```
wa_auth  : JWT（仅登录后下发）
           HttpOnly + Secure + SameSite=Strict，短期过期
           → 高价值凭证，最大限度防 XSS + CSRF

wa_guest : 不透明随机串（游客标识，如 secrets.token_urlsafe()）
           HttpOnly + Secure + SameSite=Lax，长期过期
           → 低价值标识，用于无登录时定位游客数据
```

### 解析流程（`resolve_user`）

```
1. 读 wa_auth：
   - 存在且 verify_token 成功且用户存在 → 返回登录用户（is_guest=False）
   - 存在但无效 → 直接视为「未登录」，不降级成游客
2. 读 wa_guest：
   - 不存在 → 生成新的不透明匿名 ID，标记需写回 cookie
   - 存在 → 按该 ID upsert 游客用户（is_guest=True）
3. 返回游客用户
```

要点：
- **JWT 无效 = 未登录**，绝不悄悄变成游客（堵伪造 cookie 生成游客的口子）。
- 游客标识用**加密随机值**，不当作可枚举的主键被外部直接操控。
- 登录/注册成功后：合并 `wa_guest` 对应的游客数据 → 置 `is_guest=False`、填 `email`/`password` → 用 JWT 覆盖 `wa_auth`，并可 `delete_cookie("wa_guest")`（即使保留，其优先级也低于 `wa_auth`）。

---

## 5. XSS 与 CSRF 对照

| 攻击 | 是什么 | 本方案防护 |
|---|---|---|
| XSS | 攻击者往页面塞 JS，偷凭证/冒充用户 | JWT 在 httponly cookie，JS 读不到 |
| CSRF | 借你已登录的浏览器，偷偷发你没同意的请求 | `wa_auth` 用 `SameSite=Strict`（现状）；**更强的 CSRF 防护见第 8 节（后续优化）** |

- 一句话：**XSS 是偷钥匙伪造你，CSRF 是借你浏览器冒充你。** 本方案用 httponly 挡 XSS，用 `SameSite` + 后续 CSRF token/`Origin` 校验挡 CSRF。

---

## 6. 何时需要 Authorization header（双通道）

若出现以下需求，在保留 cookie 方案的同时**并行**支持 header，后端都认：

- 开放公开 API 给第三方 / 脚本（curl、Postman）。
- 移动端 / 桌面端 App 调用。

此时形态：Web 走 httponly cookie，API 走 `Authorization: Bearer <JWT>`。

**极致安全可选 BFF Token Handler**：浏览器只拿 opaque session cookie，JWT 仅存于后端内存/Redis，前端永远接触不到 token（Curity 推荐的最安全形态，但架构更重，MVP 不必上）。

---

## 7. 落地状态（已实现）

> 2026-07-26 已完成双 cookie 分桶落地，全量测试 56 passed。详见 `reports/2026-07-26_1430_鉴权双cookie分桶落地.md`。

- [x] `wa_auth` / `wa_guest` 两个 cookie，属性分别按第 4 节设置。
- [x] `resolve_user` 改为「先验 auth、无效即未登录、再读 guest」显式逻辑。
- [x] 登录/注册成功后合并游客数据并清/覆盖 `wa_guest`。
- [x] 游客标识用 `secrets.token_urlsafe()` 等加密随机值，非 `dev_` 前缀枚举串。
- [x] 补 `tests/test_identity.py` 覆盖 `resolve_user` 双 cookie 逻辑。

### 机制实现要点

**两个 cookie，职责分离**

| Cookie | 含义 | 属性 | 生命周期 |
|---|---|---|---|
| `wa_auth` | 登录态（JWT，高价值凭证） | `HttpOnly` + `Secure` + `SameSite=Strict` | 30 天 |
| `wa_guest` | 游客标识（不透明随机串，低价值） | `HttpOnly` + `Secure` + `SameSite=Lax` | 1 年 |

两者均 `HttpOnly`（JS 读不到，抗 XSS）；`Secure` 由 `settings.cookie_secure` 控制（dev http 为 false，prod 为 true）。

**身份解析流程（`business/identity.resolve_user`）**

```
请求带 wa_auth？
 ├─ 是 → verify_token 成功且用户存在 → 返回登录用户（is_guest=False）
 └─ 否（无 cookie / JWT 失效）→ 视为「未登录」，绝不降级成游客
       └─ 读 wa_guest：
            ├─ 有 → 按该匿名 ID upsert 游客（复用同一游客）
            └─ 无 → 生成 secrets.token_urlsafe 匿名 ID，标记需写回 cookie
```

关键：auth 槽与 guest 槽完全隔离——伪造 `wa_auth` 不会变成游客账号；`wa_guest` 只存低价值随机串。

**登录 / 注册（`api/routes/auth.py`）**

- `register` / `login` → `upgrade_current_guest` 把当前游客升级为真实账号（合并雷达与渠道绑定、置 `is_guest=False`）→ 写 `wa_auth` + **清除 `wa_guest`**。
- `logout` → 同时清 `wa_auth` 与 `wa_guest`，下次请求重新生成游客。

**前端配合**

- 请求封装 `fetch` 带 `credentials: 'include'`，浏览器自动携带/存储这两个 cookie。
- 游客限额（雷达 1 / 渠道 1）由 `user.is_guest` 在业务层判定，超限返回 402 → 前端弹登录框。

**安全属性**

- 抗 XSS：JWT 在 `HttpOnly` cookie，偷不走。
- 抗 CSRF（基础）：`wa_auth` 用 `SameSite=Strict` 挡跨站伪造。
- 防身份混淆：双槽隔离，JWT 失效不会"降级"成游客凭空建号。

**已知后续优化（待做）**：见第 8 节 CSRF Token / `Origin` 校验；跨域部署时需把 `cors_origins` 由 `["*"]` 改为具体前端源。

### 数据模型：游客与真实用户同表（单表）

游客与真实用户**是同一张 `users` 表里的行**，靠 `is_guest` 布尔字段区分，没有独立的"游客表"：

- 游客：`is_guest=True`，`device_id` 有值（存 `wa_guest` 匿名 ID），`email` / `password` 为 `NULL`。
- 真实用户：`is_guest=False`，`email` 有值、`password` 为 bcrypt 哈希。
- `device_id` 与 `email` 均 `unique`：游客靠 `device_id` 定位、登录用户靠 `email` 定位，互不冲突。
- 雷达/事件/通知是独立表，经 `owner_id` / `radar_id` 关联到 `users` 行。

**为何选单表（而非拆 `guests` / `users` 两张表）**

- 游客本质是"还没填凭证的用户"，与真实用户字段高度重叠、生命周期连续（必升级为账号）。
- 单表让"升级"退化为一次事务内翻标志 + 改子表 `owner_id`，**合并零跨表迁移**；拆表则合并变成复制游客行、改所有外键指向、删游客行的真实数据迁移，复杂度与失败点都更高，而收益极低。
- `radars.owner_id` 直接引用 `users`；拆表后 owner 需能指向两张表之一，FK 约束反而变脏（多态关联或雷达也拆）。

**单表的代价与缓解**

- 可空列：`email` / `password` 对游客为 `NULL`，无法在 DB 层强制"真实用户必有 email"。
  - 缓解：应用层已校验（`upgrade_current_guest` 要求 email/password 必填、`is_guest` 判定限额），约束前移到业务层。
- `is_guest` 判定散落在业务层。
  - 缓解：集中在 `business/` 层（限额、身份解析）判断，未泄露到 DAO/模型。

**何时才该拆表**：仅当游客不再是"待升级用户"而是另一种实体（无身份、会过期的匿名会话，或字段结构与真实用户差异显著、需不同 DB 级硬约束）时才值得拆。本项目游客会持久化且必然升级，不属于此类。

> 折中方案（若未来游客专属字段明显变多）：保持 `users` 单表做核心身份，另加可选 `GuestProfile` 扩展表，而非把身份主体拆成两张表。

---

## 8. 后续优化：CSRF Token（待做）

当前 `wa_auth` 用 `SameSite=Strict` 已能挡住绝大多数跨站伪造请求，但仍有边界场景需补强 CSRF 防护：

### 为何还需要
- `SameSite=Strict` 仅防「跨站」请求；若将来 `wa_auth` 因嵌入/跨子域需求降级为 `Lax`，则会暴露给跨站顶级导航的 CSRF。
- 同站内的恶意页面（如被 XSS 注入的表单、或同站被攻陷的子域）仍可能借已登录浏览器发请求。
- 高价值写操作（改密码、删雷达、解绑渠道、改通知配置等）一旦被 CSRF 成功，危害大。

### 推荐方案（按成熟度递增）
1. **`Origin` / `Referer` 校验（最轻量，优先做）**
   - 在统一中间件/依赖里，对所有**非安全方法（POST/PUT/DELETE）**校验 `Origin` 头与本站源一致（含 scheme + host）。
   - 缺失或不匹配直接 403。对同站 XHR/fetch 天然带 `Origin`，几乎零前端改动。
2. **Double-Submit Cookie（无状态 CSRF Token）**
   - 登录时下发一个 `wa_csrf`（HttpOnly 可选；若前端要读则非 HttpOnly）随机 token；前端在写请求时把它放进 `X-CSRF-Token` header。
   - 后端比对 cookie 值与 header 值一致即放行——攻击者无法同时伪造 cookie 与 header（跨站请求带 cookie 但读不到值，也写不了同源 header）。
3. **同步器 Token（服务端会话存 token）**
   - token 存服务端会话/Redis，前端表单/请求携带，后端比对。最严但需会话存储，MVP 不必。

### 落地建议
- 先做第 1 步（`Origin` 校验），覆盖 90% 场景、成本低；
- 若未来开放跨子域/嵌入或开放公开 API，再上第 2 步（Double-Submit）。
- CSRF 防护与 `wa_auth` 的 `SameSite` 是**互补**关系，不互斥。

### 自检清单（后续）
- [ ] 新增中间件/依赖校验写请求的 `Origin` 一致性（不匹配 403）。
- [ ] 评估是否将 `wa_auth` 从 `Strict` 调整（若需跨站，配合 CSRF token 再降 `Lax`）。
- [ ] 高价值写接口（密码/删除/解绑）纳入 CSRF 强制校验范围。
- [ ] 补 CSRF 校验的测试用例（含伪造 Origin 被拒、合法 Origin 放行）。

---

## 9. 关联文件

- `src/api/deps.py` — `get_current_user` 解析 cookie。
- `src/business/identity.py` — `resolve_user` 身份识别（双 cookie 已实现）。
- `src/model/user.py` — `is_guest` / `device_id` 字段。
- `src/business/auth_service.py` — 注册/登录升级游客。
- `src/api/routes/auth.py` — 鉴权路由（写 `wa_auth` / 清 `wa_guest`）。
- `config/settings.py` — `cookie_secure` 控制 `Secure` 属性。
- `tests/test_identity.py` — `resolve_user` 双 cookie 单测。
