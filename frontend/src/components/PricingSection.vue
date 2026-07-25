<script setup>
import { ref, computed } from 'vue'

const yearly = ref(false)
const save = 0.2

const tiers = [
  {
    name: 'Scout',
    tag: 'FREE',
    monthly: 0,
    blurb: 'For casual monitoring of the things you care about.',
    feats: [
      '3 active Radars',
      'Telegram notifications',
      'Daily digest summary',
      '7-day signal history',
    ],
    cta: 'Start free',
    featured: false,
  },
  {
    name: 'Operator',
    tag: 'PRO',
    monthly: 12,
    blurb: 'For power users who live by their signals.',
    feats: [
      'Unlimited Radars',
      'Priority AI filtering',
      'Multi-channel (TG · Email · Slack)',
      'Real-time push + webhooks',
      '90-day signal history',
    ],
    cta: 'Go Pro',
    featured: true,
  },
  {
    name: 'Command',
    tag: 'TEAM',
    monthly: 39,
    blurb: 'For teams running shared intelligence at scale.',
    feats: [
      'Everything in Operator',
      'Shared team Radars',
      'API & Zapier access',
      'SSO & role controls',
      'Unlimited history + export',
    ],
    cta: 'Contact sales',
    featured: false,
  },
]

const priceFor = (m) => (m === 0 ? '0' : yearly.value ? Math.round(m * (1 - save)) : m)
</script>

<template>
  <section class="pricing" id="pricing">
    <div class="wrap">
      <header class="pricing__head" v-reveal>
        <p class="eyebrow">// PRICING</p>
        <h2 class="pricing__title">Plans that scale with your curiosity.</h2>
        <p class="pricing__sub">Start free. Upgrade the moment a signal actually matters.</p>

        <div class="toggle" role="tablist" aria-label="Billing period">
          <button
            class="toggle__opt"
            :class="{ 'is-on': !yearly }"
            @click="yearly = false"
          >Monthly</button>
          <button
            class="toggle__opt"
            :class="{ 'is-on': yearly }"
            @click="yearly = true"
          >
            Yearly
            <span class="toggle__save mono">−20%</span>
          </button>
        </div>
      </header>

      <div class="tiers">
        <article
          v-for="(t, i) in tiers"
          :key="t.name"
          class="tier"
          :class="{ 'tier--featured': t.featured }"
          v-reveal="i + 1"
        >
          <span v-if="t.featured" class="tier__badge mono">MOST POPULAR</span>
          <div class="tier__top">
            <span class="tier__tag mono">{{ t.tag }}</span>
            <h3 class="tier__name">{{ t.name }}</h3>
            <p class="tier__blurb">{{ t.blurb }}</p>
          </div>

          <div class="tier__price">
            <span class="tier__cur">$</span>
            <span class="tier__amt">{{ priceFor(t.monthly) }}</span>
            <span class="tier__per mono">/ {{ t.monthly === 0 ? 'forever' : 'mo' }}</span>
          </div>
          <p v-if="yearly && t.monthly > 0" class="tier__note mono">
            billed yearly · ${{ t.monthly * 12 * (1 - save) | 0 }}/yr
          </p>

          <a
            class="btn tier__cta"
            :class="t.featured ? 'btn-primary' : 'btn-ghost'"
            href="#top"
          >{{ t.cta }}</a>

          <ul class="tier__feats">
            <li v-for="f in t.feats" :key="f">
              <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
                <path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span>{{ f }}</span>
            </li>
          </ul>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.pricing {
  padding: 110px 0;
}
.pricing__head {
  text-align: center;
  margin-bottom: 52px;
}
.pricing__title {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: clamp(32px, 4.4vw, 50px);
  letter-spacing: -0.02em;
  margin-top: 14px;
}
.pricing__sub {
  color: var(--muted);
  font-size: 17px;
  margin: 14px auto 30px;
  max-width: 460px;
}

/* billing toggle */
.toggle {
  display: inline-flex;
  gap: 4px;
  padding: 5px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 999px;
}
.toggle__opt {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--muted);
  padding: 9px 18px;
  border-radius: 999px;
  transition: color 0.2s, background 0.2s;
}
.toggle__opt.is-on {
  background: var(--lime);
  color: var(--ink);
  font-weight: 700;
}
.toggle__save {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(6, 8, 7, 0.18);
  color: inherit;
}
.toggle__opt:not(.is-on) .toggle__save {
  background: var(--line);
  color: var(--lime);
}

/* tiers */
.tiers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
  align-items: stretch;
}
.tier {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 30px 26px;
  background: linear-gradient(180deg, var(--panel-2), var(--panel));
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
.tier:hover {
  transform: translateY(-6px);
  border-color: var(--line-strong);
  box-shadow: 0 30px 60px -34px rgba(184, 255, 60, 0.35);
}
.tier--featured {
  border-color: var(--lime);
  box-shadow: 0 0 0 1px var(--lime), 0 30px 70px -30px rgba(184, 255, 60, 0.4);
}
.tier__badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--ink);
  background: var(--lime);
  padding: 5px 12px;
  border-radius: 999px;
  font-weight: 700;
}
.tier__tag {
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--lime);
}
.tier__name {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 26px;
  margin: 8px 0 10px;
}
.tier__blurb {
  color: var(--muted);
  font-size: 14px;
  min-height: 42px;
}
.tier__price {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin: 22px 0 4px;
}
.tier__cur {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 22px;
  color: var(--text);
}
.tier__amt {
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 52px;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--text);
}
.tier__per {
  font-size: 13px;
  color: var(--muted-2);
  margin-left: 4px;
}
.tier__note {
  font-size: 11px;
  color: var(--muted-2);
  min-height: 16px;
  margin-bottom: 20px;
}
.tier__cta {
  justify-content: center;
  width: 100%;
  margin-bottom: 24px;
}
.tier__feats {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: auto;
}
.tier__feats li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 14px;
  color: var(--text);
}
.tier__feats svg {
  flex: none;
  margin-top: 2px;
  color: var(--lime);
}

@media (max-width: 880px) {
  .tiers { grid-template-columns: 1fr; max-width: 420px; margin: 0 auto; }
  .tier--featured { order: -1; }
}
</style>
