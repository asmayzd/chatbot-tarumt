<script setup>
import { ref } from "vue";
import LoginView from "./views/LoginView.vue";
import DashboardView from "./views/DashboardView.vue";

const user = ref(null);

function onLoggedIn(data) { user.value = data; }
function onLogout() { user.value = null; }
</script>

<template>
  <LoginView v-if="!user" @logged-in="onLoggedIn" />
  <DashboardView v-else :user="user" @logout="onLogout" />
</template>
