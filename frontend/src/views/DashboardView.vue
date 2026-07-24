<script setup>
import { ref, computed, onMounted } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "../components/Icons.js";
import Mascot from "../components/Mascot.vue";
import SecurityDashboard from "../components/SecurityDashboard.vue";
import BiDashboard from "../components/BiDashboard.vue";
import { t } from "../i18n.js";

const props = defineProps({ user: Object });
const emit = defineEmits(["logout"]);

const activeView = ref("chat"); // "chat" | "security" (admin only) | "bi" (admin / analyst)

const T = computed(() => t.value.chat);

const kpis = ref(null);
const suggestions = ref([]);
const messages = ref([
  { role: "assistant", content: T.value.welcome },
]);
const input = ref("");
const loading = ref(false);

// --- Historique de conversations persistant (mémoire de chat) ---
const sessions = ref([]);
const currentSessionId = ref(null);
const sessionsLoading = ref(false);

// État de la mascotte : idle / thinking / talking
const mascotState = ref("idle");
let talkTimer = null;

// Effet machine à écrire
const typing = ref(false);
let typeTimer = null;

/**
 * Révèle le texte caractère par caractère.
 * La vitesse s'adapte : une réponse longue s'écrit plus vite pour
 * ne pas faire attendre l'utilisateur.
 */
function typeOut(message, fullText) {
  return new Promise((resolve) => {
    const speed = fullText.length > 260 ? 8 : 18;
    let i = 0;
    typing.value = true;

    if (typeTimer) clearInterval(typeTimer);
    typeTimer = setInterval(() => {
      i += 1;
      message.content = fullText.slice(0, i);
      if (i >= fullText.length) {
        clearInterval(typeTimer);
        typeTimer = null;
        typing.value = false;
        resolve();
      }
    }, speed);
  });
}

/** Un clic sur la bulle affiche immédiatement toute la réponse. */
function skipTyping() {
  if (!typing.value || !pendingFull) return;
  if (typeTimer) clearInterval(typeTimer);
  typeTimer = null;
  pendingMessage.content = pendingFull;
  typing.value = false;
}

let pendingMessage = null;
let pendingFull = "";

onMounted(async () => {
  if (props.user.can_view_bi) {
    try { kpis.value = await api.kpis(); } catch (e) { /* ignore */ }
  }
  try {
    const s = await api.suggestions();
    suggestions.value = s.suggestions;
  } catch (e) { /* ignore */ }

  await loadSessions();
  if (sessions.value.length > 0) {
    await openSession(sessions.value[0].session_id);
  }
  // Sinon : pas de conversation existante, on garde le message d'accueil local ;
  // /ask en créera une automatiquement dès la première question.
});

async function loadSessions() {
  sessionsLoading.value = true;
  try {
    const res = await api.listSessions();
    sessions.value = res.sessions;
  } catch (e) {
    /* ignore */
  } finally {
    sessionsLoading.value = false;
  }
}

async function openSession(sessionId) {
  if (sessionId === currentSessionId.value) return;
  try {
    const res = await api.getSessionMessages(sessionId);
    currentSessionId.value = sessionId;
    messages.value = res.messages.length
      ? res.messages
      : [{ role: "assistant", content: T.value.welcome }];
  } catch (e) {
    /* ignore */
  }
}

function startNewChat() {
  currentSessionId.value = null;
  messages.value = [{ role: "assistant", content: T.value.welcome }];
}

async function removeSession(sessionId, evt) {
  evt.stopPropagation();
  try {
    await api.deleteSession(sessionId);
  } catch (e) {
    /* ignore */
  }
  const wasCurrent = sessionId === currentSessionId.value;
  await loadSessions();
  if (wasCurrent) {
    if (sessions.value.length > 0) {
      currentSessionId.value = null; // force reload even if same id ordering
      await openSession(sessions.value[0].session_id);
    } else {
      startNewChat();
    }
  }
}

async function send(question) {
  const q = (question || input.value).trim();
  if (!q || loading.value) return;

  messages.value.push({ role: "user", content: q });
  input.value = "";
  loading.value = true;
  mascotState.value = "thinking";

  let fullText;
  let sql = null;
  let blocked = false;

  try {
    const res = await api.ask(q, currentSessionId.value);
    fullText = res.content;
    sql = res.sql;
    blocked = !!res.blocked;
    if (res.session_id && res.session_id !== currentSessionId.value) {
      currentSessionId.value = res.session_id;
    }
    loadSessions(); // rafraîchit la liste (nouvelle conversation / titre auto)
  } catch (e) {
    fullText = "Error: " + e.message;
  }

  loading.value = false;

  // Une alerte de sécurité s'affiche d'un coup, sans effet machine à écrire :
  // ce n'est pas une réponse conversationnelle, elle doit se voir immédiatement.
  if (blocked) {
    messages.value.push({ role: "assistant", content: fullText, sql: null, blocked: true });
    mascotState.value = "idle";
    return;
  }

  // Bulle vide, puis le texte s'écrit dedans pendant que la mascotte parle.
  messages.value.push({ role: "assistant", content: "", sql: null });

  // IMPORTANT : on récupère la référence réactive renvoyée par le tableau.
  // Muter l'objet brut poussé ci-dessus ne déclencherait aucun re-render.
  const message = messages.value[messages.value.length - 1];
  pendingMessage = message;
  pendingFull = fullText;

  mascotState.value = "talking";
  if (talkTimer) clearTimeout(talkTimer);

  await typeOut(message, fullText);

  // Le détail SQL n'apparaît qu'une fois la phrase terminée.
  message.sql = sql;
  pendingMessage = null;
  pendingFull = "";
  mascotState.value = "idle";
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
        <span class="row-ic"><span class="ic" v-html="ICONS.chart"></span> {{ T.biAnalytics }}:</span>
        <span :class="user.can_view_bi ? 'ok' : 'no'">
          {{ user.can_view_bi ? T.granted : T.restricted }}
        </span>
      </div>

      <button
        v-if="user.can_view_bi"
        :class="['nav-toggle', 'bi', { active: activeView === 'bi' }]"
        @click="activeView = activeView === 'bi' ? 'chat' : 'bi'"
      >
        <span class="ic" v-html="ICONS.chart"></span>
        {{ activeView === 'bi' ? T.backToChat : T.biAnalytics }}
      </button>

      <button
        v-if="user.role === 'admin'"
        :class="['nav-toggle', { active: activeView === 'security' }]"
        @click="activeView = activeView === 'security' ? 'chat' : 'security'"
      >
        <span class="ic" v-html="ICONS.shield"></span>
        {{ activeView === 'security' ? T.backToChat : T.cybersecurity }}
      </button>

      <button class="new-chat" @click="startNewChat">{{ T.newChat }}</button>

      <div class="sessions">
        <button
          v-for="s in sessions"
          :key="s.session_id"
          :class="['session-item', { active: s.session_id === currentSessionId }]"
          @click="openSession(s.session_id)"
        >
          <span class="session-name">{{ s.session_name }}</span>
          <span class="session-del" @click="removeSession(s.session_id, $event)">&times;</span>
        </button>
        <p v-if="!sessionsLoading && sessions.length === 0" class="no-sessions">
          {{ T.noSessions }}
        </p>
      </div>

      <button class="logout" @click="logout"><span class="ic" v-html="ICONS.logout"></span> {{ T.logout }}</button>
    </aside>

    <!-- Main -->
    <main class="main">
      <template v-if="activeView === 'chat'">
      <div class="hero">
        <div class="hero-text">
          <h1>{{ T.heroTitle }}</h1>
          <p>{{ T.heroDesc }}</p>
          <span class="badge">{{ T.connected }}: {{ user.customer_name }} — {{ user.role }}</span>
        </div>
        <Mascot :state="mascotState" :size="140" class="hero-mascot" />
      </div>

      <!-- KPI cards -->
      <div v-if="kpis" class="kpis">
        <div class="kpi">
          <div class="kpi-ic sales" v-html="ICONS.sales"></div>
          <div class="kpi-label">{{ T.totalSales }}</div>
          <div class="kpi-value">{{ money(kpis.total_sales) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-ic profit" v-html="ICONS.profit"></div>
          <div class="kpi-label">{{ T.totalProfit }}</div>
          <div class="kpi-value">{{ money(kpis.total_profit) }}</div>
        </div>
        <div class="kpi">
          <div class="kpi-ic anomaly" v-html="ICONS.anomaly"></div>
          <div class="kpi-label">{{ T.anomalies }}</div>
          <div class="kpi-value">{{ kpis.anomalies.toLocaleString() }}</div>
        </div>
      </div>
      <div v-else-if="!user.can_view_bi" class="restricted">
        {{ T.biRestricted }}
      </div>

      <!-- Chat -->
      <div class="chat">
        <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role, { blocked: m.blocked }]">
          <div class="bubble" @click="skipTyping">
            <span v-if="m.blocked" class="alert-ic" v-html="ICONS.shield"></span>
            {{ m.content }}<span
              v-if="typing && i === messages.length - 1"
              class="caret"
            ></span>
            <details v-if="m.sql" class="sql">
              <summary><span class="ic" v-html="ICONS.sql"></span> {{ T.sqlUsed }}</summary>
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
        <input v-model="input" :placeholder="T.inputPlaceholder" @keyup.enter="send()" />
        <button @click="send()" :disabled="loading">{{ T.send }}</button>
      </div>
      </template>

      <BiDashboard v-else-if="activeView === 'bi' && user.can_view_bi" />

      <SecurityDashboard v-else-if="activeView === 'security' && user.role === 'admin'" />
    </main>
  </div>
</template>

<style scoped>
/* ============================================================
   LAYOUT
   ============================================================ */
.layout {
  display: flex;
  min-height: 100vh;
  align-items: stretch;
}

.main {
  flex: 1;
  min-width: 0;              /* empêche le contenu de forcer un débordement */
  padding: 26px;
  max-width: 1000px;
  margin: 0 auto;
  box-sizing: border-box;
}

/* ============================================================
   SIDEBAR
   ============================================================ */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #eef0f6;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.profile {
  background: #eef2ff;
  border: 1px solid #e0e7ff;
  border-radius: 14px;
  padding: 14px;
}
.name { font-weight: 700; color: #4338ca; display: flex; align-items: center; gap: 8px; }
.role {
  color: #6d28d9; font-size: 0.78rem; text-transform: uppercase;
  font-weight: 600; margin-top: 4px; letter-spacing: 0.04em;
}

.status {
  display: flex; justify-content: space-between; align-items: center;
  gap: 10px; font-size: 0.82rem; margin: 18px 0; color: #6b7280;
}
.ok { color: #16a34a; font-weight: 600; }
.no { color: #dc2626; font-weight: 600; }

.logout {
  width: 100%; padding: 9px; border: 1px solid #e5e7eb; border-radius: 10px;
  background: #fff; cursor: pointer; font-weight: 600;
  display: flex; align-items: center; justify-content: center; gap: 7px;
}
.logout:hover { background: #f9fafb; }

/* ============================================================
   CONVERSATIONS (historique de chat persistant)
   ============================================================ */
.new-chat {
  width: 100%; margin-top: 14px; padding: 9px; border: 1px dashed #c7d2fe;
  border-radius: 10px; background: #eef2ff; color: #4f46e5; font-weight: 600;
  cursor: pointer;
}
.new-chat:hover { background: #e0e7ff; }

.nav-toggle {
  width: 100%; margin-top: 14px; padding: 9px; border: 1px solid #fecaca;
  border-radius: 10px; background: #fff; color: #dc2626; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 7px;
}
.nav-toggle:hover { background: #fef2f2; }
.nav-toggle.active { background: #dc2626; color: #fff; border-color: #dc2626; }

.nav-toggle.bi { border-color: #c7d2fe; color: #4f46e5; }
.nav-toggle.bi:hover { background: #eef2ff; }
.nav-toggle.bi.active { background: #4f46e5; color: #fff; border-color: #4f46e5; }

.sessions {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.session-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  width: 100%; padding: 8px 10px; border: none; border-radius: 8px;
  background: transparent; color: #374151; font-size: 0.85rem; cursor: pointer;
  text-align: left;
}
.session-item:hover { background: #f3f4f6; }
.session-item.active { background: #e0e7ff; color: #4338ca; font-weight: 600; }
.session-name {
  flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.session-del {
  color: #9ca3af; font-size: 1rem; line-height: 1; padding: 0 4px; border-radius: 4px;
}
.session-del:hover { color: #dc2626; background: #fee2e2; }
.no-sessions { color: #9ca3af; font-size: 0.8rem; padding: 4px 10px; }

/* ============================================================
   HERO
   ============================================================ */
.hero {
  background: linear-gradient(120deg, #4f46e5, #7c3aed, #9333ea);
  border-radius: 20px;
  padding: 24px 28px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  box-shadow: 0 12px 30px rgba(79, 70, 229, 0.22);
}
.hero-text { flex: 1; min-width: 0; }
.hero h1 { margin: 0; font-size: 1.5rem; line-height: 1.2; }
.hero p { margin: 6px 0 0; opacity: 0.9; font-size: 0.9rem; }
.badge {
  display: inline-block; margin-top: 12px; padding: 4px 14px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px; font-size: 0.78rem;
}
.hero-mascot { flex-shrink: 0; margin-bottom: -28px; }

/* ============================================================
   KPI CARDS
   ============================================================ */
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin: 20px 0;
}
.kpi {
  background: #fff; border: 1px solid #eef0f6; border-radius: 16px;
  padding: 18px; box-shadow: 0 6px 20px rgba(17, 24, 39, 0.05);
}
.kpi-ic {
  width: 40px; height: 40px; border-radius: 11px;
  display: flex; align-items: center; justify-content: center; margin-bottom: 10px;
}
.kpi-ic.sales   { background: #e0e7ff; color: #4f46e5; }
.kpi-ic.profit  { background: #dcfce7; color: #16a34a; }
.kpi-ic.anomaly { background: #fef3c7; color: #d97706; }
.kpi-label {
  color: #6b7280; font-size: 0.78rem; text-transform: uppercase;
  font-weight: 600; letter-spacing: 0.04em;
}
.kpi-value {
  font-size: 1.6rem; font-weight: 800; color: #111827;
  margin-top: 4px; word-break: break-word;
}

.restricted {
  background: #eff6ff; border: 1px solid #dbeafe; border-radius: 12px;
  padding: 14px; color: #2563eb; margin: 20px 0;
}

/* ============================================================
   CHAT
   ============================================================ */
.chat { margin: 20px 0; }
.msg { display: flex; margin: 10px 0; }
.msg.user { justify-content: flex-end; }

.bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 16px;
  background: #f3f4f6;
  overflow-wrap: anywhere;   /* une longue valeur ne casse plus la mise en page */
  white-space: pre-line;     /* respecte les retours à la ligne envoyés par l'IA (listes numérotées) */
  line-height: 1.55;
}
.msg.user .bubble { background: #4f46e5; color: #fff; }

/* Alerte de sécurité : visuellement distincte d'une réponse normale,
   sans être criarde (pas d'animation en boucle, pas de son). */
.msg.blocked .bubble {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-weight: 600;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  animation: alert-in 0.35s ease;
}
.alert-ic {
  flex-shrink: 0;
  display: inline-flex;
  margin-top: 1px;
  color: #dc2626;
}
@keyframes alert-in {
  0%   { transform: translateX(0); }
  20%  { transform: translateX(-4px); }
  40%  { transform: translateX(4px); }
  60%  { transform: translateX(-3px); }
  80%  { transform: translateX(2px); }
  100% { transform: translateX(0); }
}
@media (prefers-reduced-motion: reduce) {
  .msg.blocked .bubble { animation: none; }
}

.sql { margin-top: 8px; }
.sql summary {
  cursor: pointer; font-size: 0.82rem; color: #6b7280;
  display: flex; align-items: center; gap: 6px;
}
.sql pre {
  background: #1e293b; color: #e2e8f0; padding: 10px; border-radius: 8px;
  overflow-x: auto;          /* le SQL long défile au lieu de déborder */
  font-size: 0.8rem; margin: 8px 0 0;
}

/* Curseur clignotant pendant l'écriture */
.caret {
  display: inline-block; width: 2px; height: 1em; margin-left: 2px;
  vertical-align: text-bottom; background: #4f46e5;
  animation: caret 0.9s steps(1) infinite;
}
@keyframes caret {
  0%, 50%   { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ============================================================
   SUGGESTIONS
   ============================================================ */
.chips {
  display: flex; flex-wrap: wrap; gap: 8px;
  align-items: flex-start; margin: 12px 0;
}
.chips button {
  border: 1px solid #e0e7ff; background: #fff; color: #4f46e5;
  border-radius: 999px; padding: 7px 18px; cursor: pointer;
  font-size: 0.85rem; transition: all 0.2s ease;
}
.chips button:hover { background: #eef2ff; transform: translateY(-1px); }

/* ============================================================
   INPUT BAR
   ============================================================ */
.input-bar { display: flex; gap: 10px; margin-top: 16px; }
.input-bar input {
  flex: 1; min-width: 0; padding: 12px 16px;
  border: 1px solid #e5e7eb; border-radius: 999px; font-size: 0.95rem;
}
.input-bar button {
  padding: 12px 24px; border: none; border-radius: 999px;
  background: #4f46e5; color: #fff; font-weight: 600; cursor: pointer;
  white-space: nowrap;
}
.input-bar button:disabled { opacity: 0.55; cursor: default; }

/* ============================================================
   ICONS
   ============================================================ */
.ic { display: inline-flex; }
.ic svg { display: block; }
.row-ic { display: inline-flex; align-items: center; gap: 6px; }

/* ============================================================
   RESPONSIVE — du plus large au plus étroit
   ============================================================ */

/* Tablette paysage : la mascotte rétrécit avant de disparaître */
@media (max-width: 900px) {
  .hero-mascot { width: 110px !important; }
}

/* Tablette / petit écran : la sidebar passe en barre horizontale */
@media (max-width: 768px) {
  .layout { flex-direction: column; }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #eef0f6;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 16px;
  }
  .profile { flex: 1; padding: 10px 12px; }
  .status { margin: 0; flex-shrink: 0; }
  .logout { width: auto; padding: 8px 16px; white-space: nowrap; }
  .new-chat, .sessions { display: none; }

  .main { padding: 16px; max-width: 100%; }
  .hero { padding: 20px; }
  .hero h1 { font-size: 1.25rem; }
  .bubble { max-width: 88%; }
}

/* Mobile : tout passe en colonne */
@media (max-width: 560px) {
  .sidebar { flex-wrap: wrap; }
  .profile { flex: 1 1 100%; }
  .status { flex: 1; }

  .hero-mascot { display: none; }
  .hero { padding: 18px; }
  .hero h1 { font-size: 1.15rem; }
  .hero p { font-size: 0.85rem; }

  .kpi-value { font-size: 1.35rem; }
  .bubble { max-width: 94%; font-size: 0.92rem; }

  .chips { flex-direction: column; }
  .chips button { width: 100%; text-align: left; font-size: 0.82rem; }

  .input-bar { flex-direction: column; }
  .input-bar button { width: 100%; }
}

/* Accessibilité : pas d'animation pour qui n'en veut pas */
@media (prefers-reduced-motion: reduce) {
  .caret { animation: none; }
  .chips button:hover { transform: none; }
}
</style>