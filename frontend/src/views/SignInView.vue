<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref('')
const password = ref('')
const show = ref(false)
const submitting = ref(false)

function submit() {
  if (submitting.value) return
  submitting.value = true
  // demo: no real backend — jump into the app
  setTimeout(() => router.push('/dashboard'), 350)
}
</script>

<template>
  <div class="auth">
    <div class="auth__glow" aria-hidden="true"></div>
    <div class="auth__card" v-reveal>
      <router-link to="/" class="auth__brand" aria-label="Back to home">
        <svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">
          <circle cx="20" cy="20" r="18" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.5" />
          <circle cx="20" cy="20" r="11" fill="none" stroke="var(--lime)" stroke-width="1.5" opacity="0.35" />
          <line x1="20" y1="20" x2="20" y2="3" stroke="var(--lime)" stroke-width="1.5" />
          <circle cx="20" cy="20" r="2.4" fill="var(--lime)" />
          <circle cx="30" cy="14" r="2" fill="var(--cyan)" />
        </svg>
        <span class="auth__name">Watch<em>Anything</em></span>
      </router-link>

      <h1 class="auth__title">Sign in</h1>
      <p class="auth__sub">Welcome back. Your radars are still watching.</p>

      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span class="field__label">Email</span>
          <input v-model="email" type="email" required placeholder="you@example.com" autocomplete="email" />
        </label>

        <label class="field">
          <span class="field__label">Password</span>
          <div class="field__pw">
            <input
              v-model="password"
              :type="show ? 'text' : 'password'"
              required
              placeholder="••••••••"
              autocomplete="current-password"
            />
            <button type="button" class="field__toggle" @click="show = !show">
              {{ show ? 'Hide' : 'Show' }}
            </button>
          </div>
        </label>

        <button class="btn btn-primary form__submit" type="submit" :disabled="submitting">
          {{ submitting ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <p class="auth__switch">
        New here? <router-link to="/signup">Create an account</router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.auth {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 110px 24px 60px;
  overflow: hidden;
}
.auth__glow {
  position: absolute;
  top: 18%;
  left: 50%;
  width: 640px;
  height: 640px;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(184, 255, 60, 0.14), transparent 62%);
  border-radius: 50%;
  pointer-events: none;
}
.auth__card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 38px 34px 30px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  box-shadow: 0 40px 90px -34px rgba(0, 0, 0, 0.85),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
.auth__brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 26px;
  filter: drop-shadow(0 0 8px rgba(184, 255, 60, 0.35));
}
.auth__name {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 19px;
}
.auth__name em {
  font-style: normal;
  color: var(--lime);
}
.auth__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 32px;
  letter-spacing: -0.02em;
}
.auth__sub {
  color: var(--muted);
  font-size: 15px;
  margin: 8px 0 26px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field__label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.field input {
  width: 100%;
  background: var(--ink);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 13px 14px;
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.field input::placeholder {
  color: var(--muted-2);
}
.field input:focus {
  outline: none;
  border-color: var(--lime);
  box-shadow: 0 0 0 3px rgba(184, 255, 60, 0.12);
}
.field__pw {
  position: relative;
  display: flex;
  align-items: center;
}
.field__pw input {
  padding-right: 58px;
}
.field__toggle {
  position: absolute;
  right: 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--muted);
  transition: color 0.2s;
}
.field__toggle:hover {
  color: var(--lime);
}
.form__submit {
  justify-content: center;
  width: 100%;
  margin-top: 6px;
  padding: 14px;
}
.form__submit:disabled {
  opacity: 0.7;
  cursor: progress;
}
.auth__switch {
  text-align: center;
  margin-top: 22px;
  font-size: 14px;
  color: var(--muted);
}
.auth__switch a {
  color: var(--lime);
  font-weight: 500;
}
.auth__switch a:hover {
  text-decoration: underline;
}
</style>
