<script setup>
import { ref, onMounted } from 'vue'
import { listRadars, listEvents, createRadar, listChannels, bindChannel } from '../services/api.js'

const radars = ref([])
const eventsByRadar = ref({})
const loading = ref(true)
const error = ref('')
const showLimit = ref(false)

const newQuery = ref('')
const creating = ref(false)

const channels = ref([])
const bindingType = ref('')

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
  showLimit.value = false
  try {
    const radar = await createRadar(newQuery.value)
    newQuery.value = ''
    await load()
    requestAnimationFrame(() => {
      document.getElementById(`radar-${radar.id}`)?.scrollIntoView({ behavior: 'smooth' })
    })
  } catch (e) {
    if (e.code === 'limit_exceeded') {
      showLimit.value = true
      error.value = e.message
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
  } catch (e) {
    if (e.code === 'limit_exceeded') {
      showLimit.value = true
      error.value = e.message
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

      <p v-if="showLimit" class="dash__limit mono">
        已达游客上限。<router-link to="/signin">登录 / 注册</router-link> 解锁更多雷达与多渠道绑定。
      </p>

      <!-- 创建框（常驻顶部，方便连续创建） -->
      <section class="onboard">
        <p class="eyebrow">// GET STARTED</p>
        <h2 class="onboard__title">创建你的<span class="hl">专属雷达</span></h2>
        <p class="onboard__sub">用一句话告诉系统你想盯住什么，它替你持续监测、命中即推送。</p>

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

        <div class="onboard__chips">
          <button v-for="ex in EXAMPLES" :key="ex" class="chip" type="button" @click="fillExample(ex)">
            {{ ex }}
          </button>
        </div>

        <div class="onboard__channels">
          <p class="onboard__channels-title">
            接收推送（可选）· <span class="mono">游客限绑 1 个渠道</span>
          </p>
          <div class="chans">
            <div v-for="c in channels" :key="c.type" class="chan" :class="{ 'is-bound': c.bound }">
              <span class="chan__type mono">{{ c.type }}</span>
              <button
                v-if="!c.bound"
                class="chan__btn"
                type="button"
                :disabled="!!bindingType"
                @click="bind(c)"
              >
                {{ bindingType === c.type ? '绑定中…' : '绑定' }}
              </button>
              <span v-else class="chan__ok mono">✓ 已绑定</span>
            </div>
          </div>
        </div>
      </section>

      <div v-if="loading" class="dash__loading mono">加载雷达中…</div>

      <section v-else class="radars">
        <p v-if="radars.length === 0" class="radars__empty mono">
          雷达创建后会出现在这里，命中事件实时流入。
        </p>
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
            <span class="radar__chan mono">{{ r.notify_channel }}</span>
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
.dash__limit {
  margin: 14px 0;
  padding: 14px 16px;
  color: var(--text);
  background: rgba(184, 255, 60, 0.07);
  border: 1px solid var(--line-strong);
  border-radius: 14px;
}
.dash__limit a { color: var(--lime); font-weight: 500; }
.dash__loading { color: var(--muted); margin-top: 24px; }

/* ---------- onboarding（常驻创建框） ---------- */
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
.onboard__form {
  display: flex;
  gap: 10px;
  margin-top: 28px;
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
.onboard__send:disabled { opacity: 0.6; cursor: default; }

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

.onboard__channels { margin-top: 38px; }
.onboard__channels-title { color: var(--muted); font-size: 14px; margin-bottom: 14px; }
.onboard__channels-title .mono { color: var(--muted-2); font-size: 12px; }
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
.chan.is-bound { border-color: var(--line-strong); }
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
.chan__ok { font-size: 12px; color: var(--cyan); }

/* ---------- 雷达列表 ---------- */
.radars {
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 40px;
}
.radars__empty {
  color: var(--muted-2);
  font-size: 13px;
  padding: 20px 0;
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
.radar__chan {
  font-size: 11px;
  color: var(--muted-2);
  border: 1px solid var(--line);
  padding: 3px 9px;
  border-radius: 6px;
}

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
