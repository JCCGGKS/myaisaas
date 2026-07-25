<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const scrolled = ref(false)
const onScroll = () => {
  scrolled.value = window.scrollY > 20
}
onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header class="nav" :class="{ 'nav--scrolled': scrolled }">
    <div class="wrap nav__inner">
      <a class="brand" href="#top">
        <span class="brand__mark" aria-hidden="true">
          <svg viewBox="0 0 40 40" width="34" height="34">
            <circle cx="20" cy="20" r="18" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.5" />
            <circle cx="20" cy="20" r="11" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.35" />
            <line x1="20" y1="20" x2="20" y2="3" stroke="var(--lime)" stroke-width="1.5" />
            <circle cx="20" cy="20" r="2.4" fill="var(--lime)" />
            <circle cx="30" cy="14" r="2" fill="var(--cyan)" />
          </svg>
        </span>
        <span class="brand__name">Watch<em>Anything</em></span>
      </a>

      <nav class="nav__links">
        <a href="#examples">Examples</a>
        <a href="#pricing">Pricing</a>
        <a href="#how">How it works</a>
      </nav>

      <div class="nav__actions">
        <router-link class="btn btn-primary" to="/signin">Sign in</router-link>
        <router-link class="btn btn-ghost" to="/dashboard">Get Started</router-link>
      </div>
    </div>
  </header>
</template>

<style scoped>
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  transition: background 0.3s ease, border-color 0.3s ease, backdrop-filter 0.3s;
  border-bottom: 1px solid transparent;
}
.nav--scrolled {
  background: rgba(6, 8, 7, 0.72);
  backdrop-filter: blur(14px);
  border-bottom-color: var(--line);
}
.nav__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand__mark {
  display: grid;
  place-items: center;
  filter: drop-shadow(0 0 8px rgba(184, 255, 60, 0.4));
}
.brand__name {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 20px;
  letter-spacing: -0.01em;
}
.brand__name em {
  font-style: normal;
  color: var(--lime);
}
.nav__links {
  display: flex;
  gap: 30px;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.05em;
}
.nav__links a {
  color: var(--muted);
  transition: color 0.2s;
  position: relative;
}
.nav__links a::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -6px;
  width: 0;
  height: 1px;
  background: var(--lime);
  transition: width 0.25s ease;
}
.nav__links a:hover {
  color: var(--text);
}
.nav__links a:hover::after {
  width: 100%;
}
.nav__actions {
  display: flex;
  align-items: center;
  gap: 18px;
}
.nav__login {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--muted);
  transition: color 0.2s;
}
.nav__login:hover {
  color: var(--lime);
}
@media (max-width: 820px) {
  .nav__links { display: none; }
}
</style>
