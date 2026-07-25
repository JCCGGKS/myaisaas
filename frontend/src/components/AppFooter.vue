<script setup>
const links = ['Pricing', 'Privacy', 'Terms', 'Contact']
</script>

<template>
  <footer class="footer">
    <div class="wrap footer__inner">
      <div class="footer__brand">
        <span class="brand__name">Watch<em>Anything</em></span>
        <p class="footer__tag">Never miss what matters.</p>
      </div>
      <nav class="footer__links">
        <a v-for="l in links" :key="l" :href="l === 'Pricing' ? '#pricing' : '#'">{{ l }}</a>
      </nav>
    </div>
    <div class="wrap footer__bottom">
      <span class="mono">© 2025 Watch Anything</span>
      <span class="mono footer__status"><i></i> all systems monitoring</span>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  border-top: 1px solid var(--line);
  padding: 56px 0 32px;
  margin-top: 40px;
  background: var(--ink-2);
}
.footer__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 24px;
}
.brand__name {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 20px;
}
.brand__name em {
  font-style: normal;
  color: var(--lime);
}
.footer__tag {
  color: var(--muted);
  font-size: 14px;
  margin-top: 6px;
}
.footer__links {
  display: flex;
  gap: 26px;
  font-family: var(--font-mono);
  font-size: 13px;
}
.footer__links a {
  color: var(--muted);
  transition: color 0.2s;
}
.footer__links a:hover {
  color: var(--lime);
}
.footer__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 40px;
  padding-top: 22px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  color: var(--muted-2);
}
.footer__status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.footer__status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--lime);
  box-shadow: 0 0 8px var(--lime);
  animation: blink 2s infinite;
}
@media (max-width: 620px) {
  .footer__bottom { flex-direction: column; gap: 10px; align-items: flex-start; }
}
</style>
