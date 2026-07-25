<script setup>
import AppNav from '../components/AppNav.vue'
import HeroSection from '../components/HeroSection.vue'
import HowItWorks from '../components/HowItWorks.vue'
import ExamplesSection from '../components/ExamplesSection.vue'
import PricingSection from '../components/PricingSection.vue'
import CtaSection from '../components/CtaSection.vue'
import AppFooter from '../components/AppFooter.vue'
</script>

<template>
  <AppNav />
  <main>
    <HeroSection />
    <HowItWorks />
    <ExamplesSection />
    <PricingSection />
    <CtaSection />
  </main>
  <AppFooter />
</template>
