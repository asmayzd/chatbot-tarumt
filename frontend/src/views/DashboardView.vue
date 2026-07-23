<script setup>
import { ref, onMounted } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "../components/Icons.js";

const props = defineProps({ user: Object });
const emit = defineEmits(["logout"]);

const kpis = ref(null);
const suggestions = ref([]);
const messages = ref([
  { role: "assistant", content: "Hello! Ask me about your data." },
]);
const input = ref("");
const loading = ref(false);

onMounted(async () => {
  if (props.user.can_view_bi) {
    try { kpis.value = await api.kpis(); } catch (e) { /* ignore */ }
  }
  try {
    const s = await api.suggestions();
    suggestions.value = s.suggestions;
  } catch (e) { /* ignore */ }
});

async function send(question) {
  const q = (question || input.value).trim();
  if (!q || loading.value) return;

  messages.value.push({ role: "user", content: q });
  input.value = "";
  loading.value = true;

  try {
    const res = await api.ask(q);
    messages.value.push({ role: "assistant", content: res.content, sql: res.sql });
  } catch (e) {
    messages.value.push({ role: "assistant", content: "Error: " + e.message });
  } finally {
    loading.value = false;
  }
}

async function logout() {
  await api.logout();
  localStorage.removeItem("token");
  emit("logout");
}

function money(v) {
  return "$" + Math.round(v).toLocaleString();
}
</script>

<template>
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="profile">
        <div class="name"><span class="ic" v-html="ICONS.user"></span> {{ user.customer_name }}</div>
        <div class="role">{{ user.role }}</div>
      </div>
      <div class="status">
        <span class="row-ic"><span class="ic" v-html="ICONS.chart"></span> BI Analytics:</span>
        <span :class="user.can_view_bi ? 'ok' : 'no'">
          {{ user.can_view_bi ? "Granted" : "Restricted" }}
        </span>
      </div>
      <button class="logout" @click="logout"><span class="ic" v-html="ICONS.logout"></span> Log out</button>
    </aside>

    <!-- Main -->
    <main class="main">
      <div class="hero">
        <h1><span class="ic-hero" v-html="ICONS.bot"></span> TARUMT Smart Assistant</h1>
        <p>Ask about sales, profits and delivery times in natural language.</p>
        <span class="badge">Connected: {{ user.customer_name }} — {{ user.role }}</span>
      </div>

      <!-- KPI cards -->
      <div v-if="kpis" class="kpis">
        <div class="kpi">
          <div class="kpi-ic sales" v-html="ICONS.sales"></div>
          <div class="kpi-label">Total Sales</div>
          <div class="kpi-value">{{ money(kpis.total_sales) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-ic profit" v-html="ICONS.profit"></div>
          <div class="kpi-label">Total Profit</div>
          <div class="kpi-value">{{ money(kpis.total_profit) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-ic anomaly" v-html="ICONS.anomaly"></div>
          <div class="kpi-label">Anomalies</div>
          <div class="kpi-value">{{ kpis.anomalies.toLocaleString() }}</div>
        </div>
      </div>
      <div v-else-if="!user.can_view_bi" class="restricted">
        The BI dashboard is reserved for analyst / admin roles.
      </div>

      <!-- Chat -->
      <div class="chat">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
          <div class="bubble">
            {{ m.content }}
            <details v-if="m.sql" class="sql">
              <summary><span class="ic" v-html="ICONS.sql"></span> SQL query used</summary>
              <pre>{{ m.sql }}</pre>
            </details>
          </div>
        </div>
        <div v-if="loading" class="msg assistant"><div class="bubble">…</div></div>
      </div>

      <!-- Suggestions -->
      <div v-if="messages.length <= 1" class="chips">
        <button v-for="s in suggestions" :key="s" @click="send(s)">{{ s }}</button>
      </div>

      <!-- Input -->
      <div class="input-bar">
        <input v-model="input" placeholder="Type your question…" @keyup.enter="send()" />
        <button @click="send()" :disabled="loading">Send</button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 240px; background: #fff; border-right: 1px solid #eef0f6; padding: 20px; }
.profile { background: #eef2ff; border: 1px solid #e0e7ff; border-radius: 14px; padding: 14px; }
.name { font-weight: 700; color: #4338ca; }
.role { color: #6d28d9; font-size: 0.78rem; text-transform: uppercase; font-weight: 600; margin-top: 4px; }
.status { display: flex; justify-content: space-between; font-size: 0.82rem; margin: 18px 0; color: #6b7280; }
.ok { color: #16a34a; font-weight: 600; }
.no { color: #dc2626; font-weight: 600; }
.logout { width: 100%; padding: 9px; border: 1px solid #e5e7eb; border-radius: 10px; background: #fff; cursor: pointer; font-weight: 600; }

.main { flex: 1; padding: 26px; max-width: 900px; }
.hero { background: linear-gradient(120deg,#4f46e5,#7c3aed,#9333ea); border-radius: 20px; padding: 24px 28px; color: #fff; }
.hero h1 { margin: 0; font-size: 1.5rem; }
.hero p { margin: 6px 0 0; opacity: 0.9; font-size: 0.9rem; }
.badge { display: inline-block; margin-top: 12px; padding: 4px 14px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.35); border-radius: 999px; font-size: 0.78rem; }

.kpis { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 20px 0; }
.kpi { background: #fff; border: 1px solid #eef0f6; border-radius: 16px; padding: 18px; }
.kpi-label { color: #6b7280; font-size: 0.78rem; text-transform: uppercase; font-weight: 600; }
.kpi-value { font-size: 1.6rem; font-weight: 800; color: #111827; margin-top: 4px; }
.restricted { background: #eff6ff; border: 1px solid #dbeafe; border-radius: 12px; padding: 14px; color: #2563eb; margin: 20px 0; }

.chat { margin: 20px 0; }
.msg { display: flex; margin: 10px 0; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 75%; padding: 12px 16px; border-radius: 16px; background: #f3f4f6; }
.msg.user .bubble { background: #4f46e5; color: #fff; }
.sql { margin-top: 8px; }
.sql pre { background: #1e293b; color: #e2e8f0; padding: 10px; border-radius: 8px; overflow-x: auto; font-size: 0.8rem; }

.chips { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; margin: 12px 0; }
.chips button { border: 1px solid #e0e7ff; background: #fff; color: #4f46e5; border-radius: 999px; padding: 7px 18px; cursor: pointer; font-size: 0.85rem; }
.chips button:hover { background: #eef2ff; }

.input-bar { display: flex; gap: 10px; margin-top: 16px; }
.input-bar input { flex: 1; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 999px; }
.input-bar button { padding: 12px 24px; border: none; border-radius: 999px; background: #4f46e5; color: #fff; font-weight: 600; cursor: pointer; }

.ic { display:inline-flex; vertical-align:middle; }
.ic svg { display:block; }
.ic-hero { display:inline-flex; vertical-align:middle; margin-right:4px; }
.row-ic { display:inline-flex; align-items:center; gap:6px; }
.kpi-ic { width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; margin-bottom:10px; }
.kpi-ic.sales { background:#e0e7ff; color:#4f46e5; }
.kpi-ic.profit { background:#dcfce7; color:#16a34a; }
.kpi-ic.anomaly { background:#fef3c7; color:#d97706; }
.logout { display:flex; align-items:center; justify-content:center; gap:7px; }
</style>