<script setup>
const steps = [
  {
    n: '01',
    title: 'Tell AI',
    desc: 'Describe what matters to you. One sentence is all it takes to spin up a Radar.',
    icon: 'M4 5h16v10H9l-5 4z',
  },
  {
    n: '02',
    title: 'AI Watches',
    desc: 'Our AI continuously scans, filters and analyzes the noise across the entire web.',
    icon: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z M12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5z',
  },
  {
    n: '03',
    title: 'Get Notified',
    desc: 'You only hear from us when something genuinely important breaks through.',
    icon: 'M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M9.5 21a2.5 2.5 0 005 0',
  },
]
</script>

<template>
  <section class="how" id="how">
    <div class="wrap">
      <header class="how__head" v-reveal>
        <p class="eyebrow">// HOW IT WORKS</p>
        <h2 class="how__title">From curiosity to signal in three steps.</h2>
      </header>

      <div class="steps">
        <div class="steps__line" aria-hidden="true"></div>
        <article
          v-for="(s, i) in steps"
          :key="s.n"
          class="step"
          v-reveal="i + 1"
        >
          <div class="step__num mono">{{ s.n }}</div>
          <div class="step__icon">
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <path :d="s.icon" />
            </svg>
          </div>
          <h3 class="step__title">{{ s.title }}</h3>
          <p class="step__desc">{{ s.desc }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.how {
  padding: 110px 0;
}
.how__head {
  text-align: center;
  margin-bottom: 64px;
}
.how__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(30px, 4vw, 46px);
  letter-spacing: -0.02em;
  margin-top: 14px;
}
.steps {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
}
.steps__line {
  position: absolute;
  top: 26px;
  left: 16%;
  right: 16%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--line-strong), transparent);
}
.step {
  position: relative;
  text-align: center;
  padding: 0 14px;
}
.step__num {
  font-size: 13px;
  color: var(--lime);
  letter-spacing: 0.1em;
}
.step__icon {
  width: 54px;
  height: 54px;
  margin: 16px auto 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--lime);
  background: var(--panel);
  border: 1px solid var(--line-strong);
  position: relative;
  z-index: 1;
  transition: transform 0.3s, box-shadow 0.3s;
}
.step:hover .step__icon {
  transform: translateY(-4px) rotate(-6deg);
  box-shadow: 0 0 26px -6px rgba(184, 255, 60, 0.5);
}
.step__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 22px;
  margin-bottom: 10px;
}
.step__desc {
  color: var(--muted);
  font-size: 15px;
  max-width: 280px;
  margin: 0 auto;
}
@media (max-width: 820px) {
  .steps {
    grid-template-columns: 1fr;
    gap: 48px;
  }
  .steps__line { display: none; }
}
</style>
