<script setup>
import { ref, computed } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "../components/Icons.js";
import { t } from "../i18n.js";

const T = computed(() => t.value.login);

const emit = defineEmits(["logged-in"]);
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const data = await api.login(username.value, password.value);
    localStorage.setItem("token", data.token);
    emit("logged-in", data);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="lock" v-html="ICONS.lock"></div>
      <h1>{{ T.title }}</h1>
      <p class="muted">{{ T.subtitle }}</p>

      <label>{{ T.userLabel }}</label>
      <input v-model="username" :placeholder="T.userPlaceholder" @keyup.enter="submit" />

      <label>{{ T.passwordLabel }}</label>
      <input v-model="password" type="password" placeholder="••••••••" @keyup.enter="submit" />

      <button :disabled="loading" @click="submit">
        {{ loading ? T.connecting : T.signIn }}
      </button>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-card {
  width: 360px; background: #fff; border: 1px solid #eef0f6; border-radius: 18px;
  padding: 32px; box-shadow: 0 10px 30px rgba(17,24,39,0.06); text-align: center;
}
.lock { font-size: 2.6rem; }
h1 { color: #4f46e5; font-size: 1.5rem; margin: 8px 0 4px; }
.muted { color: #6b7280; font-size: 0.88rem; margin-bottom: 22px; }
label { display: block; text-align: left; font-size: 0.8rem; color: #374151; margin: 12px 0 4px; font-weight: 600; }
input {
  width: 100%; padding: 10px 14px; border: 1px solid #e5e7eb; border-radius: 10px;
  font-size: 0.95rem; box-sizing: border-box;
}
button {
  width: 100%; margin-top: 20px; padding: 11px; border: none; border-radius: 10px;
  background: #4f46e5; color: #fff; font-weight: 600; font-size: 0.95rem; cursor: pointer;
}
button:disabled { opacity: 0.6; cursor: default; }
.error { color: #dc2626; font-size: 0.85rem; margin-top: 14px; }
</style>