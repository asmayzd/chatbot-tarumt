<script setup>
import { lang, setLang } from "../i18n.js";
</script>

<template>
  <div class="lang-switch" role="group" aria-label="Language / Langue">
    <button
      type="button"
      :class="['lang-opt', { active: lang === 'fr' }]"
      @click="setLang('fr')"
    >FR</button>
    <button
      type="button"
      :class="['lang-opt', { active: lang === 'en' }]"
      @click="setLang('en')"
    >EN</button>
  </div>
</template>

<style scoped>
.lang-switch {
  display: inline-flex;
  align-items: center;
  background: #eef2ff;
  border: 1px solid #e0e7ff;
  border-radius: 999px;
  padding: 3px;
  gap: 2px;
}
.lang-opt {
  border: none;
  background: transparent;
  color: #4f46e5;
  font-weight: 700;
  font-size: 0.76rem;
  letter-spacing: 0.02em;
  padding: 5px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.lang-opt:hover { background: rgba(79, 70, 229, 0.12); }
.lang-opt.active {
  background: #4f46e5;
  color: #fff;
}
.lang-opt.active:hover { background: #4f46e5; }
</style>
