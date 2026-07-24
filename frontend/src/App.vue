<script setup>
import { ref } from "vue";
import LoginView from "./views/LoginView.vue";
import DashboardView from "./views/DashboardView.vue";
import LangSwitch from "./components/LangSwitch.vue";

const user = ref(null);

function onLoggedIn(data) { user.value = data; }
function onLogout() { user.value = null; }
</script>

<template>
  <LangSwitch class="global-lang-switch" />
  <LoginView v-if="!user" @logged-in="onLoggedIn" />
  <DashboardView v-else :user="user" @logout="onLogout" />
</template>

<style>
.global-lang-switch {
  position: fixed;
  top: 14px;
  right: 16px;
  z-index: 100;
}
</style>
