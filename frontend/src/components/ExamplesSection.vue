<script setup>
const examples = [
  {
    tag: 'CELEB',
    title: 'LISA 官方动态',
    items: ['官方公告', '新歌 · 专辑', '演唱会信息', '品牌合作'],
  },
  {
    tag: 'TECH',
    title: 'AI 行业动态',
    items: ['新品发布', '融资 · 收购', '开源项目', '行业报告'],
  },
  {
    tag: 'CAREER',
    title: '香港教师行业',
    items: ['教师招聘', '教育政策', '薪资变化', '资格要求'],
  },
  {
    tag: 'FINANCE',
    title: '公司 / 投资',
    items: ['财报发布', '重大新闻', '股价异动', '管理层变动'],
  },
]
</script>

<template>
  <section class="examples" id="examples">
    <div class="wrap">
      <header class="examples__head" v-reveal>
        <p class="eyebrow">// POPULAR EXAMPLES</p>
        <h2 class="examples__title">Radars people are already running.</h2>
      </header>

      <div class="grid">
        <article
          v-for="(c, i) in examples"
          :key="c.title"
          class="card"
          v-reveal="i + 1"
        >
          <div class="card__top">
            <span class="card__tag mono">{{ c.tag }}</span>
            <span class="card__pulse" aria-hidden="true"></span>
          </div>
          <h3 class="card__title">{{ c.title }}</h3>
          <ul class="card__list">
            <li v-for="item in c.items" :key="item">
              <span class="card__bullet" aria-hidden="true"></span>{{ item }}
            </li>
          </ul>
          <a class="card__more" href="#">
            查看更多例子
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </a>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.examples {
  padding: 100px 0;
}
.examples__head {
  margin-bottom: 48px;
  text-align: center;
}
.examples__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(30px, 4vw, 46px);
  letter-spacing: -0.02em;
  margin-top: 14px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}
.card {
  position: relative;
  padding: 24px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
.card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(420px 200px at 100% 0%, rgba(184, 255, 60, 0.12), transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
}
.card:hover {
  transform: translateY(-6px);
  border-color: var(--line-strong);
  box-shadow: 0 26px 50px -28px rgba(184, 255, 60, 0.4);
}
.card:hover::before {
  opacity: 1;
}
.card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.card__tag {
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--lime);
  padding: 4px 9px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
}
.card__pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 10px var(--lime);
  animation: blink 2s infinite;
}
.card__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 21px;
  margin-bottom: 16px;
}
.card__list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 22px;
}
.card__list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--muted);
}
.card__bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  flex: none;
}
.card__more {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text);
  transition: gap 0.2s, color 0.2s;
}
.card__more:hover {
  color: var(--lime);
  gap: 11px;
}
</style>
