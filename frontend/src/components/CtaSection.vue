<script setup>
const features = [
  { t: 'Quick setup', d: 'Create your first Radar in under a minute.' },
  { t: 'Smart filtering', d: 'AI cuts the noise and surfaces what truly matters.' },
  { t: 'Private by default', d: 'Your data stays yours. It is never shared.' },
]
</script>

<template>
  <section class="cta" id="cta">
    <div class="cta__glow" aria-hidden="true"></div>
    <div class="wrap cta__inner" v-reveal>
      <p class="eyebrow">// GET STARTED</p>
      <h2 class="cta__title">Start your first <span class="hl">Radar.</span></h2>
      <p class="cta__sub">Free to start. No credit card required.</p>
      <router-link class="btn btn-primary cta__btn" to="/dashboard">
        Get Started Now
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </router-link>

      <div class="feats">
        <div v-for="f in features" :key="f.t" class="feat">
          <span class="feat__dot" aria-hidden="true"></span>
          <p class="feat__t">{{ f.t }}</p>
          <p class="feat__d">{{ f.d }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta {
  position: relative;
  padding: 120px 0;
  overflow: hidden;
}
.cta__glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 720px;
  height: 720px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(184, 255, 60, 0.16), transparent 60%);
  border-radius: 50%;
  border: 1px solid var(--line);
  pointer-events: none;
}
.cta__inner {
  position: relative;
  text-align: center;
}
.cta__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(38px, 6vw, 64px);
  letter-spacing: -0.02em;
  margin-top: 14px;
}
.cta__title .hl {
  color: var(--lime);
}
.cta__sub {
  color: var(--muted);
  font-size: 18px;
  margin: 16px 0 34px;
}
.cta__btn {
  font-size: 15px;
  padding: 15px 28px;
}
.feats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 70px;
  text-align: left;
}
.feat {
  padding: 22px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  transition: border-color 0.3s, transform 0.3s;
}
.feat:hover {
  border-color: var(--line-strong);
  transform: translateY(-4px);
}
.feat__dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 10px var(--lime);
  margin-bottom: 14px;
}
.feat__t {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 18px;
  margin-bottom: 6px;
}
.feat__d {
  color: var(--muted);
  font-size: 14px;
}
@media (max-width: 760px) {
  .feats { grid-template-columns: 1fr; }
}
</style>
