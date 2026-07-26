<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { listRadars, listEvents, createRadar, listChannels, bindChannel } from '../services/api.js'

const radars = ref([])
const eventsByRadar = ref({})
const loading = ref(true)
const error = ref('')
const showLimitModal = ref(false)
const limitMsg = ref('')

const newQuery = ref('')
const creating = ref(false)

const channels = ref([])
const bindingType = ref('')
const showBindModal = ref(false)

// 已绑定的渠道（同框内先绑后建）
const boundChannel = computed(() => channels.value.find((c) => c.bound) || null)

const EXAMPLES = [
  'LISA 演唱会与新歌动态',
  'OpenAI 与 AI Agent 行业动态',
  '竞品融资与产品发布新闻',
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [rs, chs] = await Promise.all([listRadars(), listChannels()])
    radars.value = rs
    channels.value = chs
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

async function addRadar() {
  if (!newQuery.value.trim() || creating.value) return
  creating.value = true
  showLimitModal.value = false
  try {
    // 渠道可选：未绑定时传空值占位（"未绑定"），不阻断创建
    const channel = boundChannel.value?.type || ''
    const radar = await createRadar(newQuery.value, channel)
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

async function bind(c) {
  if (c.bound || bindingType.value) return
  bindingType.value = c.type
  try {
    const res = await bindChannel(c.type)
    const idx = channels.value.findIndex((x) => x.type === c.type)
    if (idx >= 0) channels.value[idx] = res
    // 绑定后关闭弹窗并刷新（后端会回填雷达的 notify_channel）
    showBindModal.value = false
    await load()
  } catch (e) {
    if (e.code === 'limit_exceeded') {
      showLimitModal.value = true
      limitMsg.value = e.message
      error.value = ''
    } else {
      error.value = e.message || '绑定失败'
    }
  } finally {
    bindingType.value = ''
  }
}

const fmtTime = (iso) => {
  const d = new Date(iso)
  return d.toLocaleString()
}

// 雷达绑定的渠道列表：优先取 channels 数组（多通道），兼容旧的单值 notify_channel
const radarChannels = (r) =>
  Array.isArray(r.channels) ? r.channels : r.notify_channel ? [r.notify_channel] : []

onMounted(load)
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
        <router-link to="/" class="btn btn-ghost dash__back">← 返回首页</router-link>
      </header>

      <p v-if="error" class="dash__error mono">{{ error }}</p>

      <!-- 同框：先绑推送渠道，再创建雷达 -->
      <section class="onboard">
        <p class="eyebrow">// GET STARTED</p>
        <h2 class="onboard__title">创建你的<span class="hl">专属雷达</span></h2>
        <p class="onboard__sub">一句话告诉系统你想盯住什么，并先绑定一个推送渠道，命中即通知你。</p>

        <!-- ① 渠道（同框） -->
        <div class="onboard__step">
          <span class="onboard__stepnum mono">1</span>
          <div class="onboard__stepbody">
            <p class="onboard__steptitle">推送渠道（可选）</p>
            <div class="chans">
              <div v-for="c in channels" :key="c.type" class="chan">
                <span class="chan__type mono">{{ c.type }}</span>
                <button
                  class="chan__btn"
                  type="button"
                  :disabled="!!bindingType || c.bound"
                  @click="bind(c)"
                >
                  {{ bindingType === c.type ? '绑定中…' : '绑定' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ② 创建（同框，需先绑渠道） -->
        <div class="onboard__step">
          <span class="onboard__stepnum mono">2</span>
          <div class="onboard__stepbody">
            <p class="onboard__steptitle">创建雷达</p>
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
            <p v-if="!boundChannel" class="onboard__hint mono">
              💡 推送渠道可选：绑定后命中的事件会主动通知你；不绑定也能直接创建雷达。
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
              <button class="radar__chan radar__chan--btn mono" type="button" @click="showBindModal = true">
                点击绑定
              </button>
            </div>
          </div>

          <div class="radar__events">
            <p v-if="!eventsByRadar[r.id] || eventsByRadar[r.id].length === 0" class="radar__noev mono">
              暂无命中事件 — 监测持续进行中。
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
                <div class="event__meta mono">
                  <span>score {{ ev.relevance_score?.toFixed(2) }}</span>
                  <span>{{ fmtTime(ev.created_at) }}</span>
                </div>
              </div>
            </a>
          </div>
        </article>
      </section>

      <!-- 绑定渠道弹窗：点击雷达卡片「未绑定」时弹出 -->
      <transition name="fade">
        <div v-if="showBindModal" class="modal" @click.self="showBindModal = false">
          <div class="modal__card">
            <button class="modal__close" type="button" @click="showBindModal = false" aria-label="关闭">×</button>
            <p class="eyebrow">// BIND CHANNEL</p>
            <h3 class="modal__title">绑定推送渠道</h3>
            <p class="modal__sub">选择并绑定一个渠道，雷达命中的事件会主动通知你。</p>
            <div class="chans">
              <div v-for="c in channels" :key="c.type" class="chan">
                <span class="chan__type mono">{{ c.type }}</span>
                <button
                  class="chan__btn"
                  type="button"
                  :disabled="!!bindingType || c.bound"
                  @click="bind(c)"
                >
                  {{ bindingType === c.type ? '绑定中…' : '绑定' }}
                </button>
              </div>
            </div>
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
.event__meta {
  display: flex;
  gap: 14px;
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted-2);
}

@media (max-width: 620px) {
  .dash__head { flex-direction: column; align-items: flex-start; }
  .onboard { padding: 32px 22px 36px; }
  .onboard__form { flex-direction: column; }
  .onboard__send { width: 100%; }
}
</style>
