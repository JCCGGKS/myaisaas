<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createRadar } from '../services/api.js'

const router = useRouter()
const examples = ['Lisa', 'OpenAI', 'Hong Kong teacher jobs', 'AI Agent industry']

const query = ref('')
const submitting = ref(false)

function fillExample(e) {
  query.value = e
}

async function submit() {
  if (!query.value.trim() || submitting.value) return
  submitting.value = true
  try {
    const radar = await createRadar(query.value)
    router.push('/dashboard')
  } catch (err) {
    // 出错时仍跳转，由 Dashboard 展示错误；此处不阻塞体验
    router.push('/dashboard')
  } finally {
    submitting.value = false
  }
}

const chat = [
  { me: true, text: 'Monitor LISA — 演唱会 & 新歌 🎤' },
  {
    bot: true,
    tag: 'LISA 官方动态',
    title: 'Lisa 确认加盟科切拉音乐节，4 月登台',
    time: '2m',
    dot: 'var(--lime)',
  },
  {
    bot: true,
    tag: 'LISA 新歌',
    title: '新单曲空降 Billboard 榜首，48h 播放破亿',
    time: '18m',
    dot: 'var(--cyan)',
  },
  {
    bot: true,
    tag: 'LISA 品牌合作',
    title: '官宣出任某奢侈品牌全球代言人，大片明日释出',
    time: '41m',
    dot: 'var(--amber)',
  },
]
</script>

<template>
  <section class="hero" id="top">
    <!-- ambient radar glow -->
    <div class="hero__ambient" aria-hidden="true"></div>

    <div class="wrap hero__grid">
      <div class="hero__copy">
        <p class="eyebrow hero__eyebrow">// AI SIGNAL MONITORING</p>
        <h1 class="hero__title">
          Never miss what <span class="hl">matters.</span>
        </h1>
        <p class="hero__sub">
          Tell AI what you care about, and get notified the moment something
          important happens — straight to your phone.
        </p>

        <form class="monitor" @submit.prevent="submit">
          <span class="monitor__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20">
              <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2" />
              <line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
          </span>
          <input
            class="monitor__input"
            type="text"
            v-model="query"
            placeholder="What would you like me to monitor?"
            aria-label="What would you like me to monitor?"
          />
          <button class="monitor__send" type="submit" :disabled="submitting" aria-label="Start monitoring">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M4 12h15M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </form>

        <div class="chips">
          <span class="chips__label mono">try:</span>
          <button v-for="e in examples" :key="e" class="chip" type="button" @click="fillExample(e)">{{ e }}</button>
        </div>

        <div class="proof">
          <div class="proof__stars" aria-hidden="true">
            <svg v-for="n in 5" :key="n" viewBox="0 0 20 20" width="16" height="16">
              <path
                d="M10 1.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L10 15.9 4.8 17.6l1-5.8L1.5 7.7l5.9-.9z"
                fill="var(--lime)"
              />
            </svg>
          </div>
          <p class="proof__text">Join <strong>1,000+</strong> people who trust Watch Anything</p>
        </div>
      </div>

      <!-- Phone mockup: Telegram-style bot pushes -->
      <div class="phone-wrap" aria-hidden="true">
        <div class="phone">
          <div class="phone__notch"></div>
          <div class="phone__screen">
            <div class="phone__status">
              <span class="mono">9:41</span>
              <span class="phone__bars">
                <i></i><i></i><i></i>
                <svg viewBox="0 0 18 12" width="18" height="12"><path d="M1 11l4-4 3 3 5-6 4 4v5H1z" fill="currentColor"/></svg>
              </span>
            </div>

            <div class="botbar">
              <span class="botbar__avatar">
                <svg viewBox="0 0 40 40" width="38" height="38">
                  <circle cx="20" cy="20" r="18" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.6" />
                  <circle cx="20" cy="20" r="11" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.4" />
                  <line x1="20" y1="20" x2="20" y2="3" stroke="var(--lime)" stroke-width="1.5" />
                  <circle cx="20" cy="20" r="2.4" fill="var(--lime)" />
                  <circle cx="30" cy="14" r="2" fill="var(--cyan)" />
                </svg>
              </span>
              <div class="botbar__meta">
                <p class="botbar__name">Watch Anything Bot</p>
                <p class="botbar__status mono"><i></i> monitoring your radars</p>
              </div>
              <span class="botbar__live mono">LIVE</span>
            </div>

            <div class="chat">
              <div
                v-for="(m, i) in chat"
                :key="i"
                class="msg"
                :class="m.me ? 'msg--me' : 'msg--bot'"
                :style="{ animationDelay: 0.5 + i * 0.5 + 's' }"
              >
                <template v-if="m.me">
                  <p class="msg__bubble msg__bubble--me">{{ m.text }}</p>
                </template>
                <template v-else>
                  <div class="signal">
                    <span class="signal__dot" :style="{ background: m.dot }"></span>
                    <div class="signal__body">
                      <div class="signal__top">
                        <span class="signal__tag mono">{{ m.tag }}</span>
                        <span class="signal__time mono">{{ m.time }}</span>
                      </div>
                      <p class="signal__title">{{ m.title }}</p>
                    </div>
                  </div>
                </template>
              </div>

              <!-- typing indicator -->
              <div class="msg msg--bot typing" :style="{ animationDelay: 0.5 + chat.length * 0.5 + 's' }">
                <div class="signal signal--typing">
                  <span class="typing__dot"></span>
                  <span class="typing__dot"></span>
                  <span class="typing__dot"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="phone__glow" aria-hidden="true"></div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  padding: 150px 0 90px;
  overflow: hidden;
}
.hero__ambient {
  position: absolute;
  top: -8%;
  right: -6%;
  width: 620px;
  height: 620px;
  background: conic-gradient(
    from 0deg,
    rgba(184, 255, 60, 0.18),
    rgba(184, 255, 60, 0.02) 40deg,
    transparent 70deg,
    transparent 360deg
  );
  border-radius: 50%;
  filter: blur(4px);
  opacity: 0.5;
  animation: sweep 9s linear infinite;
  pointer-events: none;
}
.hero__grid {
  display: grid;
  grid-template-columns: 1.02fr 0.98fr;
  gap: 56px;
  align-items: center;
  position: relative;
  z-index: 1;
}
.hero__eyebrow {
  margin-bottom: 18px;
  animation: floatIn 0.7s ease both;
}
.hero__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(44px, 6vw, 76px);
  line-height: 1.02;
  letter-spacing: -0.02em;
  animation: floatIn 0.7s ease 0.06s both;
}
.hero__title .hl {
  color: var(--lime);
  position: relative;
}
.hero__title .hl::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  height: 10px;
  background: rgba(184, 255, 60, 0.18);
  z-index: -1;
  border-radius: 4px;
}
.hero__sub {
  color: var(--muted);
  font-size: 18px;
  margin: 22px 0 30px;
  max-width: 460px;
  animation: floatIn 0.7s ease 0.12s both;
}

.monitor {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--panel);
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 8px 8px 8px 18px;
  max-width: 480px;
  transition: border-color 0.25s, box-shadow 0.25s;
  animation: floatIn 0.7s ease 0.18s both;
}
.monitor:focus-within {
  border-color: var(--lime);
  box-shadow: 0 0 0 4px rgba(184, 255, 60, 0.12);
}
.monitor__icon {
  color: var(--muted);
  display: grid;
  place-items: center;
}
.monitor__input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
}
.monitor__input::placeholder {
  color: var(--muted-2);
}
.monitor__send {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--lime);
  color: var(--ink);
  transition: transform 0.2s, box-shadow 0.2s;
}
.monitor__send:hover {
  transform: scale(1.06);
  box-shadow: 0 0 22px -2px rgba(184, 255, 60, 0.6);
}

.chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
  animation: floatIn 0.7s ease 0.24s both;
}
.chips__label {
  font-size: 12px;
  color: var(--muted-2);
}
.chip {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text);
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  transition: all 0.2s;
}
.chip:hover {
  border-color: var(--lime);
  color: var(--lime);
  transform: translateY(-2px);
}

.proof {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 30px;
  animation: floatIn 0.7s ease 0.3s both;
}
.proof__stars {
  display: flex;
  gap: 2px;
}
.proof__text {
  font-size: 14px;
  color: var(--muted);
}
.proof__text strong {
  color: var(--text);
}

/* ---------- Phone ---------- */
.phone-wrap {
  position: relative;
  display: grid;
  place-items: center;
  animation: floatIn 0.9s ease 0.2s both;
}
.phone {
  position: relative;
  width: min(300px, 78vw);
  aspect-ratio: 300 / 610;
  background: linear-gradient(160deg, #11201a, #0a120e);
  border: 1px solid var(--line-strong);
  border-radius: 44px;
  padding: 12px;
  box-shadow:
    0 50px 90px -34px rgba(0, 0, 0, 0.9),
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 0 0 6px rgba(6, 8, 7, 0.6);
}
.phone__notch {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  width: 96px;
  height: 22px;
  background: #060807;
  border-radius: 999px;
  z-index: 3;
}
.phone__screen {
  position: relative;
  height: 100%;
  border-radius: 34px;
  overflow: hidden;
  background:
    radial-gradient(120% 80% at 50% -10%, rgba(184, 255, 60, 0.08), transparent 60%),
    linear-gradient(180deg, #0c1410, #080d0b);
  display: flex;
  flex-direction: column;
}
.phone__status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 22px 8px;
  font-size: 12px;
  color: var(--text);
}
.phone__bars {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--text);
}
.phone__bars i {
  width: 3px;
  background: currentColor;
  border-radius: 1px;
}
.phone__bars i:nth-child(1) { height: 5px; }
.phone__bars i:nth-child(2) { height: 8px; }
.phone__bars i:nth-child(3) { height: 11px; }

.botbar {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px 16px 12px;
  border-bottom: 1px solid var(--line);
}
.botbar__avatar {
  display: grid;
  place-items: center;
  filter: drop-shadow(0 0 7px rgba(184, 255, 60, 0.4));
}
.botbar__meta { flex: 1; }
.botbar__name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 14px;
  color: var(--text);
}
.botbar__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--muted-2);
  margin-top: 2px;
}
.botbar__status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 7px var(--lime);
  animation: blink 1.8s infinite;
}
.botbar__live {
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--lime);
  border: 1px solid var(--line-strong);
  padding: 3px 7px;
  border-radius: 6px;
}

.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 14px 18px;
  overflow: hidden;
}
.msg {
  opacity: 0;
  animation: floatIn 0.55s ease forwards;
}
.msg--me {
  display: flex;
  justify-content: flex-end;
}
.msg__bubble--me {
  background: linear-gradient(135deg, var(--lime-deep), var(--lime-dim));
  color: #06120a;
  font-size: 12.5px;
  font-weight: 500;
  padding: 9px 13px;
  border-radius: 16px 16px 5px 16px;
  max-width: 78%;
  line-height: 1.4;
}

.signal {
  display: flex;
  gap: 10px;
  padding: 11px 12px;
  background: rgba(184, 255, 60, 0.05);
  border: 1px solid var(--line);
  border-radius: 14px 14px 14px 5px;
  max-width: 90%;
}
.signal__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
}
.signal__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 3px;
}
.signal__tag {
  font-size: 10px;
  color: var(--lime);
  letter-spacing: 0.04em;
}
.signal__time {
  font-size: 10px;
  color: var(--muted-2);
}
.signal__title {
  font-size: 12.5px;
  color: var(--text);
  line-height: 1.4;
}

.signal--typing {
  align-items: center;
  gap: 5px;
  background: transparent;
  border-style: dashed;
}
.typing__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted);
  animation: blink 1.2s infinite;
}
.typing__dot:nth-child(2) { animation-delay: 0.2s; }
.typing__dot:nth-child(3) { animation-delay: 0.4s; }

.phone__glow {
  position: absolute;
  inset: -10% -14%;
  z-index: -1;
  background: radial-gradient(circle at 50% 50%, rgba(184, 255, 60, 0.22), transparent 62%);
  filter: blur(20px);
  pointer-events: none;
}

@media (max-width: 900px) {
  .hero__grid {
    grid-template-columns: 1fr;
    gap: 52px;
  }
  .hero { padding-top: 120px; }
  .phone-wrap { order: 2; }
}
</style>
