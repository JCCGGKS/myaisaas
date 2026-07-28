<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { listRadars, listEvents, createRadar, listChannels, bindChannel, unbindChannel, deleteRadar, getMe, logout } from '../services/api.js'
import { registerPush, isPushSupported } from '../services/push.js'

const radars = ref([])
const eventsByRadar = ref({})
const loading = ref(true)
const error = ref('')
// 绑定/解绑失败的错误弹窗（以弹窗形式展现，避免与创建雷达的错误混淆）
const showErrorModal = ref(false)
const errorModalMsg = ref('')
const showLimitModal = ref(false)
const limitMsg = ref('')

// 当前登录态：游客（is_guest=true）或已登录账号
const me = ref(null)
const loggingOut = ref(false)

const newQuery = ref('')
const creating = ref(false)

// 绑定弹窗：绑定跟随雷达，弹窗内操作的是「当前雷达」的渠道
const channels = ref([])
const currentRadarId = ref(null)
const bindingType = ref('')
const unbindingType = ref('')
const showBindModal = ref(false)
// 真实后端绑定 email/webhook 需要 recipient；按渠道类型分别暂存
const bindRecipients = ref({})
// telegram 绑定后后端返回 connect_url，引导用户打开完成 bot 连接
const telegramConnect = ref('')

// 各渠道绑定引导提示：帮助用户知道「要去哪拿到接收地址」
function chanHint(type) {
  if (type === 'feishu') {
    return '飞书机器人依附于群聊，但你可以新建一个「只有自己」的群当作私人收件箱：飞书 → 新建群（只拉你自己）→ 设置 → 群机器人 → 添加「自定义机器人」，复制其 Webhook 地址（形如 https://open.feishu.cn/open-apis/bot/v2/hook/...）粘贴到上方，绑定即生效。若机器人开启了「签名校验」，请联系管理员在后端配置签名密钥。'
  }
  if (type === 'email') {
    return '绑定后我们会发送一封验证邮件，点击邮件内链接即可激活（本地开发自动激活）。'
  }
  if (type === 'webpush') {
    return '点击「允许通知并订阅」后，命中事件会以浏览器原生通知推送到本设备（关页面也能收）。无需绑定第三方账号。'
  }
  return ''
}

// 不同渠道的输入框占位符
function chanPlaceholder(type) {
  if (type === 'email') return '你的邮箱地址'
  if (type === 'feishu') return '飞书机器人 Webhook 地址'
  return 'Webhook URL'
}

// webpush 不需要 recipient 输入框，改为点击订阅按钮
function chanNeedsInput(type) {
  return type !== 'webpush' && type !== 'telegram'
}

const EXAMPLES = [
  'LISA 演唱会与新歌动态',
  'OpenAI 与 AI Agent 行业动态',
  '竞品融资与产品发布新闻',
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [rs, meRes] = await Promise.all([listRadars(), getMe()])
    radars.value = rs
    me.value = meRes
    await Promise.all(
      rs.map(async (r) => {
        eventsByRadar.value[r.id] = await listEvents(r.id)
      })
    )
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function doLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logout()
  } catch {
    /* 即便后端失败也按已登出处理，刷新即可 */
  } finally {
    me.value = { is_guest: true, email: null }
    loggingOut.value = false
    await load()
  }
}

async function addRadar() {
  if (!newQuery.value.trim() || creating.value) return
  creating.value = true
  showLimitModal.value = false
  try {
    // 绑定跟随雷达：创建时不携带渠道，渠道在雷达卡片内单独绑定
    const radar = await createRadar(newQuery.value)
    newQuery.value = ''
    await load()
    nextTick(() => {
      document.getElementById(`radar-${radar.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  } catch (e) {
    if (e.code === 'limit_exceeded') {
      showLimitModal.value = true
      limitMsg.value = e.message
      error.value = ''
    } else {
      error.value = e.message || '创建失败'
    }
  } finally {
    creating.value = false
  }
}

function fillExample(ex) {
  newQuery.value = ex
}

// 删除雷达：确认后删除（后端联删其下事件），刷新列表
const deleting = ref(false)
async function removeRadar(r) {
  if (deleting.value) return
  if (!window.confirm(`确定删除雷达「${r.raw_query}」？其下的事件也会一并删除。`)) return
  deleting.value = true
  try {
    await deleteRadar(r.id)
    await load()
  } catch (e) {
    error.value = e.message || '删除失败'
  } finally {
    deleting.value = false
  }
}

// 打开某雷达的绑定弹窗：加载该雷达的实际绑定状态（绑定跟随雷达，互不继承）
async function openBind(r) {
  currentRadarId.value = r.id
  showBindModal.value = true
  telegramConnect.value = ''
  errorModalMsg.value = ''
  try {
    channels.value = await listChannels(r.id)
  } catch (e) {
    error.value = e.message || '加载渠道失败'
  }
}

async function bind(c) {
  if (c.bound || bindingType.value) return
  bindingType.value = c.type
  try {
    // webpush：走浏览器订阅流程（权限 -> SW -> subscribe -> 绑定）
    if (c.type === 'webpush') {
      await registerPush(currentRadarId.value, bindChannel)
      channels.value = await listChannels(currentRadarId.value)
      await load()
      return
    }
    // telegram 无需 recipient；email/webhook 取对应输入
    const recipient = c.type === 'telegram' ? '' : bindRecipients.value[c.type] || ''
    const res = await bindChannel(currentRadarId.value, c.type, recipient)
    // telegram 需打开 connect_url 完成连接：保留弹窗展示链接
    if (c.type === 'telegram' && res.connect_url) {
      telegramConnect.value = res.connect_url
      channels.value = await listChannels(currentRadarId.value)
      return
    }
    telegramConnect.value = ''
    if (c.type !== 'telegram') bindRecipients.value[c.type] = ''
    // 刷新弹窗内（当前雷达）与雷达卡片的绑定状态
    channels.value = await listChannels(currentRadarId.value)
    await load()
  } catch (e) {
    if (e.code === 'limit_exceeded') {
      showLimitModal.value = true
      limitMsg.value = e.message
    } else {
      errorModalMsg.value = e.message || '绑定失败'
      showErrorModal.value = true
    }
  } finally {
    bindingType.value = ''
  }
}

// 解绑：从当前雷达移除该渠道
async function unbind(c) {
  if (!c.bound || unbindingType.value) return
  unbindingType.value = c.type
  try {
    await unbindChannel(currentRadarId.value, c.type)
    channels.value = await listChannels(currentRadarId.value)
    await load()
  } catch (e) {
    errorModalMsg.value = e.message || '解绑失败'
    showErrorModal.value = true
  } finally {
    unbindingType.value = ''
  }
}

const fmtTime = (iso) => {
  const d = new Date(iso)
  return d.toLocaleString()
}

// 雷达已绑定渠道：优先解析 notify_channels（list[dict]，元素含 channel_type）；
// 兼容旧字段 channels（list[str]）/ notify_channel（单值字符串）。绑定跟随雷达，每个雷达独立。
const radarChannels = (r) => {
  const list = Array.isArray(r.notify_channels)
    ? r.notify_channels
    : Array.isArray(r.channels)
      ? r.channels
      : r.notify_channel
        ? [r.notify_channel]
        : []
  return list
    .map((b) => (typeof b === 'string' ? b : b?.channel_type))
    .filter(Boolean)
}

// 短轮询：监控循环会持续产出真实事件，定时刷新让事件流自动出现（无需手动演示）
const REFRESH_MS = 30_000
let refreshTimer = null
const refreshing = ref(false)

function refresh() {
  if (refreshing.value || loading.value) return
  refreshing.value = true
  load().finally(() => {
    refreshing.value = false
  })
}

onMounted(() => {
  load()
  refreshTimer = setInterval(() => {
    if (!loading.value && !refreshing.value) load()
  }, REFRESH_MS)
})
onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="dash">
    <div class="wrap dash__inner">
      <header class="dash__head">
        <div>
          <p class="eyebrow">// DASHBOARD</p>
          <h1 class="dash__title">Your <span class="hl">Radars</span></h1>
          <p class="dash__sub">持续监测中 — 命中即推送，这里是你所有雷达的事件流。</p>
        </div>
        <div class="dash__head-right">
          <!-- 登录态：游客提示 / 已登录账号 -->
          <div v-if="me" class="who" :class="{ 'who--guest': me.is_guest }">
            <template v-if="me.is_guest">
              <span class="who__badge mono">游客模式</span>
              <router-link to="/signin" class="who__link">登录 / 注册解锁更多 →</router-link>
            </template>
            <template v-else>
              <span class="who__email mono">{{ me.name || me.email }}</span>
              <button class="who__logout mono" type="button" :disabled="loggingOut" @click="doLogout">
                {{ loggingOut ? '退出中…' : '退出' }}
              </button>
            </template>
          </div>
          <router-link to="/" class="btn btn-ghost dash__back">← 返回首页</router-link>
        </div>
      </header>

      <p v-if="error" class="dash__error mono">{{ error }}</p>

      <!-- 同框：先绑推送渠道，再创建雷达 -->
      <section class="onboard">
        <p class="eyebrow">// GET STARTED</p>
        <h2 class="onboard__title">创建你的<span class="hl">专属雷达</span></h2>
        <p class="onboard__sub">一句话告诉系统你想盯住什么</p>

        <!-- 创建（可用渠道清单由后端 JSON 配置加载，绑定在雷达卡片内完成） -->
        <div class="onboard__step">
          <span class="onboard__stepnum mono">1</span>
          <div class="onboard__stepbody">
            <p class="onboard__steptitle">创建雷达（创建后可在下方卡片点击「点击绑定」关联推送渠道，命中即通知你）</p>
            <form class="onboard__form" @submit.prevent="addRadar">
              <input
                v-model="newQuery"
                class="onboard__input"
                type="text"
                placeholder="例如：LISA 演唱会与新歌动态"
                aria-label="新建雷达"
              />
              <button class="btn btn-primary onboard__send" type="submit" :disabled="creating">
                {{ creating ? '创建中…' : '创建雷达' }}
              </button>
            </form>
            <p class="onboard__hint mono">
              💡 推送渠道可选：雷达创建后可在下方卡片内单独绑定渠道，命中即通知你；不绑定也能直接创建雷达。每个雷达的绑定相互独立。
            </p>
            <div class="onboard__chips">
              <button v-for="ex in EXAMPLES" :key="ex" class="chip" type="button" @click="fillExample(ex)">
                {{ ex }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <div v-if="loading" class="dash__loading mono">加载雷达中…</div>

      <!-- 雷达列表：创建后才出现，并显示绑定的具体渠道类型 -->
      <section v-if="radars.length > 0" class="radars">
        <article
          v-for="r in radars"
          :key="r.id"
          :id="`radar-${r.id}`"
          class="radar"
          v-reveal
        >
          <div class="radar__top">
            <span class="radar__live mono" :class="{ 'is-off': !r.active }">
              {{ r.active ? 'LIVE' : 'PAUSED' }}
            </span>
            <h2 class="radar__query">{{ r.raw_query }}</h2>
            <div class="radar__chans">
              <span v-for="ch in radarChannels(r)" :key="ch" class="radar__chan mono">{{ ch }}</span>
              <button class="radar__chan radar__chan--btn mono" type="button" @click="openBind(r)">
                {{ radarChannels(r).length ? '管理绑定' : '点击绑定' }}
              </button>
            </div>
            <button class="radar__del mono" type="button" :disabled="deleting" @click="removeRadar(r)">
              ✕ 删除
            </button>
          </div>

          <div class="radar__events">
            <div class="radar__events-head">
              <span class="radar__events-title mono">事件流</span>
              <div class="radar__events-actions">
                <button class="radar__seed mono" type="button" :disabled="refreshing" @click="refresh">
                  {{ refreshing ? '刷新中…' : '↻ 刷新' }}
                </button>
              </div>
            </div>
            <p v-if="!eventsByRadar[r.id] || eventsByRadar[r.id].length === 0" class="radar__noev mono">
              暂无命中事件 — 监测持续进行中，命中即推送。
            </p>
            <a
              v-for="ev in eventsByRadar[r.id]"
              :key="ev.id"
              class="event"
              :href="ev.source_url"
              target="_blank"
              rel="noopener"
            >
              <span class="event__dot"></span>
              <div class="event__body">
                <p class="event__title">{{ ev.title }}</p>
                <p v-if="ev.summary && ev.summary !== ev.title" class="event__summary">{{ ev.summary }}</p>
                <div class="event__meta mono">
                  <span>score {{ ev.relevance_score?.toFixed(2) }}</span>
                  <span v-for="ch in (ev.pushed_channels || [])" :key="ch" class="event__ch">{{ ch }}</span>
                  <span>{{ fmtTime(ev.created_at) }}</span>
                </div>
              </div>
            </a>
          </div>
        </article>
      </section>

      <!-- 绑定渠道弹窗：点击雷达卡片「绑定/管理绑定」时弹出，操作当前雷达的渠道 -->
      <transition name="fade">
        <div v-if="showBindModal" class="modal" @click.self="showBindModal = false">
          <div class="modal__card">
            <button class="modal__close" type="button" @click="showBindModal = false" aria-label="关闭">×</button>
            <p class="eyebrow">// BIND CHANNEL</p>
            <h3 class="modal__title">绑定推送渠道</h3>
            <p class="modal__sub">
              为雷达「<strong>{{ radars.find((r) => r.id === currentRadarId)?.raw_query }}</strong>」绑定渠道，命中的事件会主动通知你。绑定仅作用于本雷达。
            </p>
            <div class="chans">
              <div v-for="c in channels" :key="c.type" class="chan chan--col">
                <div class="chan__row">
                  <span class="chan__type mono">{{ c.type }}</span>
                  <span
                    v-if="c.bound"
                    class="chan__status mono"
                    :class="c.verified ? 'is-ok' : 'is-pending'"
                  >{{ c.bound ? (c.verified ? '已绑定' : '待验证') : '' }}</span>
                </div>
                <input
                  v-if="chanNeedsInput(c.type)"
                  v-model="bindRecipients[c.type]"
                  class="chan__input"
                  type="text"
                  :placeholder="chanPlaceholder(c.type)"
                  :disabled="!!bindingType || c.bound"
                />
                <p v-if="c.type === 'webpush' && !isPushSupported()" class="chan__hint">
                  当前环境不支持 Web Push：Service Worker 与通知 API 仅可在 <strong>http://localhost</strong> 或 <strong>https</strong> 下使用。请改用 localhost 访问前端（不要用局域网 IP），并确认浏览器未禁用通知。
                </p>
                <p v-if="c.recipient" class="chan__recipient mono">{{ c.recipient }}</p>
                <p v-if="chanHint(c.type)" class="chan__hint">{{ chanHint(c.type) }}</p>
                <div class="chan__actions">
                  <button
                    v-if="!c.bound"
                    class="chan__btn"
                    type="button"
                    :disabled="!!bindingType"
                    @click="bind(c)"
                  >
                    {{ bindingType === c.type ? '处理中…' : (c.type === 'webpush' ? '允许通知并订阅' : '绑定') }}
                  </button>
                  <button
                    v-else
                    class="chan__btn chan__btn--unbind"
                    type="button"
                    :disabled="!!unbindingType"
                    @click="unbind(c)"
                  >
                    {{ unbindingType === c.type ? '解绑中…' : '解绑' }}
                  </button>
                </div>
              </div>
            </div>
            <p v-if="telegramConnect" class="bind__connect mono">
              请打开链接完成 Telegram 连接：
              <a :href="telegramConnect" target="_blank" rel="noopener">{{ telegramConnect }}</a>
            </p>
          </div>
        </div>
      </transition>

      <!-- 游客限额弹窗：命中上限（雷达/渠道）时弹出，引导登录/注册 -->
      <transition name="fade">
        <div v-if="showLimitModal" class="modal" @click.self="showLimitModal = false">
          <div class="modal__card">
            <button class="modal__close" type="button" @click="showLimitModal = false" aria-label="关闭">×</button>
            <p class="eyebrow">// GUEST LIMIT</p>
            <h3 class="modal__title">已达游客上限</h3>
            <p class="modal__sub">{{ limitMsg }}</p>
            <div class="modal__actions">
              <router-link to="/signin" class="btn btn-primary" @click="showLimitModal = false">登录 / 注册解锁</router-link>
              <button class="btn btn-ghost" type="button" @click="showLimitModal = false">稍后再说</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 通用错误弹窗：绑定/解绑等操作失败时的提示 -->
      <transition name="fade">
        <div v-if="showErrorModal" class="modal" @click.self="showErrorModal = false">
          <div class="modal__card">
            <button class="modal__close" type="button" @click="showErrorModal = false" aria-label="关闭">×</button>
            <p class="eyebrow">// ERROR</p>
            <h3 class="modal__title">操作失败</h3>
            <p class="modal__sub mono">{{ errorModalMsg }}</p>
            <div class="modal__actions">
              <button class="btn btn-primary" type="button" @click="showErrorModal = false">我知道了</button>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.dash {
  padding: 120px 0 90px;
  min-height: 100vh;
}
.dash__inner { max-width: 880px; }
.dash__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 36px;
}
.dash__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(36px, 5vw, 56px);
  letter-spacing: -0.02em;
  margin-top: 12px;
}
.dash__title .hl { color: var(--lime); }
.dash__sub { color: var(--muted); margin-top: 12px; max-width: 460px; }
.dash__back { font-size: 13px; }
.dash__head-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}
.who {
  display: flex;
  align-items: center;
  gap: 12px;
}
.who__badge {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--amber);
  border: 1px solid var(--amber);
  border-radius: 6px;
  padding: 4px 9px;
}
.who__link {
  font-size: 13px;
  color: var(--lime);
}
.who__link:hover { text-decoration: underline; }
.who__email {
  font-size: 13px;
  color: var(--text);
}
.who__logout {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--muted);
  background: none;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  padding: 5px 10px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.who__logout:hover:not(:disabled) { color: var(--text); border-color: var(--lime); }
.who__logout:disabled { opacity: 0.6; cursor: default; }

.dash__error { color: var(--amber); margin: 14px 0; }
.dash__loading { color: var(--muted); margin-top: 24px; }

/* ---------- onboarding（同框：绑渠道 + 创建） ---------- */
.onboard {
  margin-top: 8px;
  padding: 44px 40px 48px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
}
.onboard__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(30px, 4.5vw, 46px);
  letter-spacing: -0.02em;
  margin-top: 12px;
}
.onboard__title .hl { color: var(--lime); }
.onboard__sub { color: var(--muted); margin-top: 12px; max-width: 480px; }

.onboard__step {
  display: flex;
  gap: 16px;
  margin-top: 30px;
  padding-top: 26px;
  border-top: 1px solid var(--line);
}
.onboard__step:first-of-type { border-top: none; padding-top: 0; margin-top: 26px; }
.onboard__stepnum {
  flex: none;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 12px;
  color: var(--lime);
  border: 1px solid var(--line-strong);
}
.onboard__stepbody { flex: 1; min-width: 0; }
.onboard__steptitle {
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 14px;
}

.onboard__form {
  display: flex;
  gap: 10px;
}
.onboard__input {
  flex: 1;
  background: var(--ink);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.onboard__input::placeholder { color: var(--muted-2); }
.onboard__input:focus {
  outline: none;
  border-color: var(--lime);
  box-shadow: 0 0 0 3px rgba(184, 255, 60, 0.12);
}
.onboard__send { font-size: 14px; padding: 14px 24px; white-space: nowrap; }
.onboard__send:disabled { opacity: 0.5; cursor: not-allowed; }

.onboard__hint {
  margin-top: 14px;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.5;
}
.onboard__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}
.chip {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--muted);
  background: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}
.chip:hover { color: var(--text); border-color: var(--lime); }

/* ---------- 渠道 ---------- */
.chans { display: flex; flex-wrap: wrap; gap: 12px; }
.chan {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  background: var(--ink);
  border: 1px solid var(--line);
  border-radius: 12px;
  transition: border-color 0.2s;
}
.chan__type { font-size: 12px; color: var(--text); text-transform: uppercase; letter-spacing: 0.08em; }
.chan__btn {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--lime);
  background: none;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.chan__btn:hover:not(:disabled) { background: rgba(184, 255, 60, 0.1); }
.chan__btn:disabled { opacity: 0.5; cursor: default; }
.chan--col { flex-direction: column; align-items: stretch; gap: 8px; }
.chan__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.chan__status {
  font-size: 10px;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid var(--line-strong);
}
.chan__status.is-ok { color: var(--lime); border-color: var(--lime); }
.chan__status.is-pending { color: var(--amber); border-color: var(--amber); }
.chan__recipient {
  font-size: 11px;
  color: var(--muted);
  word-break: break-all;
}
.chan__actions { display: flex; gap: 10px; }
.chan__btn--unbind {
  color: var(--amber);
  border-color: var(--amber);
}
.chan__btn--unbind:hover:not(:disabled) { background: rgba(255, 176, 32, 0.12); }
.chan__input {
  background: var(--ink);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 12px;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 13px;
}
.chan__input::placeholder { color: var(--muted-2); }
.chan__input:focus { outline: none; border-color: var(--lime); }
.chan__hint {
  margin: -2px 0 2px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
  background: rgba(184, 255, 60, 0.06);
  border-left: 2px solid var(--lime);
  border-radius: 4px;
  padding: 8px 10px;
}
.bind__connect {
  margin-top: 16px;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.6;
  word-break: break-all;
}
.bind__connect a { color: var(--lime); }

/* ---------- 雷达列表（创建后出现） ---------- */
.radars {
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 40px;
}
.radar {
  padding: 24px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  scroll-margin-top: 110px;
}
.radar__top {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.radar__live {
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--lime);
  border: 1px solid var(--line-strong);
  padding: 3px 8px;
  border-radius: 6px;
}
.radar__live.is-off { color: var(--muted-2); }
.radar__query {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 19px;
  flex: 1;
}
.radar__chans {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}
.radar__chan {
  font-size: 11px;
  color: var(--muted-2);
  border: 1px solid var(--line);
  padding: 3px 9px;
  border-radius: 6px;
}
.radar__chan--btn {
  color: var(--amber);
  border-color: var(--amber);
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.radar__chan--btn:hover {
  background: rgba(255, 176, 32, 0.12);
  color: var(--amber);
  border-color: var(--amber);
}
.radar__del {
  flex: none;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--muted-2);
  background: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 11px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}
.radar__del:hover:not(:disabled) {
  color: var(--amber);
  border-color: var(--amber);
  background: rgba(255, 176, 32, 0.1);
}
.radar__del:disabled { opacity: 0.5; cursor: default; }

/* ---------- 绑定渠道弹窗 ---------- */
.modal {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.55);
}
.modal__card {
  position: relative;
  width: 100%;
  max-width: 460px;
  padding: 32px 30px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  box-shadow: 0 40px 90px -34px rgba(0, 0, 0, 0.85);
}
.modal__close {
  position: absolute;
  top: 14px;
  right: 16px;
  font-size: 22px;
  line-height: 1;
  color: var(--muted);
  background: none;
  border: none;
  cursor: pointer;
}
.modal__close:hover { color: var(--text); }
.modal__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 26px;
  margin-top: 10px;
}
.modal__sub {
  color: var(--muted);
  margin-top: 10px;
  margin-bottom: 22px;
  font-size: 14px;
}
.modal__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.modal__actions .btn { font-size: 14px; padding: 12px 20px; }
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

.radar__events { display: flex; flex-direction: column; gap: 10px; }
.radar__events-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.radar__events-actions { display: flex; gap: 8px; }
.radar__events-title {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted-2);
}
.radar__seed {
  font-size: 11px;
  color: var(--cyan);
  background: none;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  padding: 5px 11px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.radar__seed:hover:not(:disabled) {
  background: rgba(80, 220, 240, 0.1);
  border-color: var(--cyan);
}
.radar__seed:disabled { opacity: 0.5; cursor: default; }
.radar__noev { color: var(--muted-2); font-size: 13px; }
.event {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(184, 255, 60, 0.05);
  border: 1px solid var(--line);
  border-radius: 14px;
  transition: border-color 0.2s, transform 0.2s;
}
.event:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.event__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
}
.event__body { flex: 1; }
.event__title { font-size: 14.5px; color: var(--text); line-height: 1.45; }
.event__summary {
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.event__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted-2);
}
.event__ch {
  color: var(--lime);
  border: 1px solid var(--line-strong);
  border-radius: 5px;
  padding: 1px 6px;
}

@media (max-width: 620px) {
  .dash__head { flex-direction: column; align-items: flex-start; }
  .onboard { padding: 32px 22px 36px; }
  .onboard__form { flex-direction: column; }
  .onboard__send { width: 100%; }
}
</style>
