<script setup>
import { ref, onMounted } from 'vue'
import { listRadars, listEvents, createRadar } from '../services/api.js'

const radars = ref([])
const eventsByRadar = ref({})
const loading = ref(true)
const error = ref('')

const newQuery = ref('')
const creating = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    radars.value = await listRadars()
    await Promise.all(
      radars.value.map(async (r) => {
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
  try {
    const radar = await createRadar(newQuery.value)
    newQuery.value = ''
    await load()
    // 滚动到新雷达
    requestAnimationFrame(() => {
      document.getElementById(`radar-${radar.id}`)?.scrollIntoView({ behavior: 'smooth' })
    })
  } catch (e) {
    error.value = e.message || '创建失败'
  } finally {
    creating.value = false
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

      <form class="newradar" @submit.prevent="addRadar">
        <span class="newradar__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18">
            <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </span>
        <input
          v-model="newQuery"
          class="newradar__input"
          type="text"
          placeholder="新建雷达：想盯住什么？"
          aria-label="新建雷达"
        />
        <button class="newradar__send btn btn-primary" type="submit" :disabled="creating">
          {{ creating ? '创建中…' : '创建' }}
        </button>
      </form>

      <p v-if="error" class="dash__error mono">{{ error }}</p>

      <div v-if="loading" class="dash__loading mono">加载雷达中…</div>

      <div v-else-if="radars.length === 0" class="dash__empty">
        <p>还没有雷达。在上方创建一个，开始监测你关心的一切。</p>
      </div>

      <section v-else class="radars">
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

.newradar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 8px 8px 8px 18px;
  transition: border-color 0.25s, box-shadow 0.25s;
}
.newradar:focus-within {
  border-color: var(--lime);
  box-shadow: 0 0 0 4px rgba(184, 255, 60, 0.12);
}
.newradar__icon { color: var(--muted); display: grid; place-items: center; }
.newradar__input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
}
.newradar__input::placeholder { color: var(--muted-2); }
.newradar__send { font-size: 13px; padding: 11px 20px; }
.newradar__send:disabled { opacity: 0.6; cursor: default; }

.dash__error { color: var(--amber); margin: 14px 0; }
.dash__loading { color: var(--muted); }
.dash__empty {
  margin-top: 40px;
  padding: 40px;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-lg);
}

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
}
</style>
