<script setup>
import { ref, onMounted, computed } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "./Icons.js";

const overview = ref(null);
const events = ref([]);
const loading = ref(true);
const statusFilter = ref("");
const hovered = ref(null); // { day, attacks, failed_logins, x, y }

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "BLOCKED,CRITICAL", label: "Attacks (blocked / critical)" },
  { value: "FAILED", label: "Failed logins" },
  { value: "SUCCESS", label: "Success" },
];

async function loadAll() {
  loading.value = true;
  try {
    const [ov, ev] = await Promise.all([
      api.securityOverview(),
      api.securityEvents({ limit: 100, status: statusFilter.value || undefined }),
    ]);
    overview.value = ov;
    events.value = ev.events;
  } catch (e) {
    /* ignore */
  } finally {
    loading.value = false;
  }
}

onMounted(loadAll);

const chartWidth = 560;
const chartHeight = 180;
const barGap = 3;

const chartData = computed(() => {
  const rows = overview.value?.timeseries || [];
  const max = Math.max(1, ...rows.map((r) => Math.max(r.attacks, r.failed_logins)));
  const dayWidth = rows.length ? chartWidth / rows.length : chartWidth;
  const barWidth = Math.max(2, (dayWidth - barGap * 3) / 2);

  return rows.map((r, i) => {
    const x = i * dayWidth;
    const attacksH = (r.attacks / max) * (chartHeight - 24);
    const failedH = (r.failed_logins / max) * (chartHeight - 24);
    return {
      ...r,
      x,
      dayWidth,
      barWidth,
      attacksH,
      failedH,
      attacksY: chartHeight - 20 - attacksH,
      failedY: chartHeight - 20 - failedH,
      label: r.day.slice(5), // MM-DD
    };
  });
});

function showTooltip(d, evt) {
  const rect = evt.currentTarget.closest("svg").getBoundingClientRect();
  hovered.value = { ...d, cx: evt.clientX - rect.left, cy: evt.clientY - rect.top };
}
function hideTooltip() {
  hovered.value = null;
}

function statusClass(status) {
  if (status === "SUCCESS") return "st-ok";
  if (status === "FAILED") return "st-warn";
  if (status === "BLOCKED" || status === "CRITICAL") return "st-critical";
  return "st-muted";
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString();
}
</script>

<template>
  <div class="security">
    <div class="security-head">
      <h2><span class="ic" v-html="ICONS.shield"></span> Cybersecurity</h2>
      <button class="refresh" @click="loadAll" :disabled="loading">
        {{ loading ? "Loading…" : "Refresh" }}
      </button>
    </div>

    <!-- KPI cards -->
    <div v-if="overview" class="sec-kpis">
      <div class="sec-kpi">
        <div class="sec-kpi-label">Events (24h)</div>
        <div class="sec-kpi-value">{{ overview.kpis.events_24h }}</div>
      </div>
      <div class="sec-kpi warn">
        <div class="sec-kpi-label">Failed logins (24h)</div>
        <div class="sec-kpi-value">{{ overview.kpis.failed_logins_24h }}</div>
      </div>
      <div class="sec-kpi critical">
        <div class="sec-kpi-label">Attacks blocked (24h)</div>
        <div class="sec-kpi-value">{{ overview.kpis.attacks_24h }}</div>
      </div>
      <div class="sec-kpi">
        <div class="sec-kpi-label">Banned accounts</div>
        <div class="sec-kpi-value">{{ overview.kpis.total_bans }}</div>
      </div>
    </div>

    <!-- Chart : attacks & failed logins, last 14 days -->
    <div v-if="overview && chartData.length" class="sec-chart-card">
      <div class="sec-chart-title">Attacks &amp; failed logins — last 14 days</div>
      <div class="sec-legend">
        <span class="legend-item"><span class="dot critical"></span> Attacks blocked</span>
        <span class="legend-item"><span class="dot warn"></span> Failed logins</span>
      </div>
      <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="sec-chart" preserveAspectRatio="none">
        <line
          v-for="gy in [0, 0.5, 1]"
          :key="gy"
          :x1="0" :x2="chartWidth"
          :y1="chartHeight - 20 - gy * (chartHeight - 24)"
          :y2="chartHeight - 20 - gy * (chartHeight - 24)"
          class="grid-line"
        />
        <g v-for="d in chartData" :key="d.day">
          <rect
            :x="d.x + barGap"
            :y="d.attacksY"
            :width="d.barWidth"
            :height="Math.max(1, d.attacksH)"
            rx="2"
            class="bar critical"
            @mousemove="showTooltip(d, $event)"
            @mouseleave="hideTooltip"
          />
          <rect
            :x="d.x + barGap * 2 + d.barWidth"
            :y="d.failedY"
            :width="d.barWidth"
            :height="Math.max(1, d.failedH)"
            rx="2"
            class="bar warn"
            @mousemove="showTooltip(d, $event)"
            @mouseleave="hideTooltip"
          />
          <text :x="d.x + d.dayWidth / 2" :y="chartHeight - 6" class="axis-label">{{ d.label }}</text>
        </g>
      </svg>
      <div
        v-if="hovered"
        class="sec-tooltip"
        :style="{ left: hovered.cx + 'px', top: hovered.cy + 'px' }"
      >
        <strong>{{ hovered.day }}</strong>
        <div>Attacks: {{ hovered.attacks }}</div>
        <div>Failed logins: {{ hovered.failed_logins }}</div>
      </div>
    </div>

    <!-- Events table -->
    <div class="sec-events-card">
      <div class="sec-events-head">
        <div class="sec-chart-title">Recent security events</div>
        <select v-model="statusFilter" @change="loadAll">
          <option v-for="opt in STATUS_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>
      <div class="sec-table-wrap">
        <table class="sec-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Role</th>
              <th>Action</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in events" :key="e.event_id">
              <td class="nowrap">{{ formatTime(e.created_at) }}</td>
              <td>{{ e.username }}</td>
              <td>{{ e.role }}</td>
              <td>{{ e.action }}</td>
              <td><span :class="['status-pill', statusClass(e.status)]">{{ e.status }}</span></td>
              <td class="details">{{ e.details }}</td>
            </tr>
            <tr v-if="!loading && events.length === 0">
              <td colspan="6" class="empty">No events found.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.security { margin: 20px 0; }
.security-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;
}
.security-head h2 {
  display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1.25rem; color: #111827;
}
.ic { display: inline-flex; color: #dc2626; }
.refresh {
  padding: 7px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;
  cursor: pointer; font-weight: 600; font-size: 0.85rem;
}
.refresh:hover { background: #f9fafb; }

/* KPIs */
.sec-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 18px;
}
.sec-kpi {
  background: #fff; border: 1px solid #eef0f6; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(17,24,39,0.04);
}
.sec-kpi-label { color: #6b7280; font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.sec-kpi-value { font-size: 1.5rem; font-weight: 800; color: #111827; margin-top: 4px; }
.sec-kpi.warn .sec-kpi-value { color: #b45309; }
.sec-kpi.critical .sec-kpi-value { color: #dc2626; }

/* Chart */
.sec-chart-card, .sec-events-card {
  background: #fff; border: 1px solid #eef0f6; border-radius: 16px; padding: 16px 18px; margin-bottom: 18px;
  box-shadow: 0 4px 14px rgba(17,24,39,0.04);
}
.sec-chart-title { font-weight: 700; color: #111827; font-size: 0.95rem; margin-bottom: 8px; }
.sec-legend { display: flex; gap: 16px; margin-bottom: 10px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #6b7280; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot.critical, .bar.critical { fill: #dc2626; background: #dc2626; }
.dot.warn, .bar.warn { fill: #d97706; background: #d97706; }

.sec-chart { width: 100%; height: 190px; overflow: visible; }
.grid-line { stroke: #f0f1f5; stroke-width: 1; }
.axis-label { font-size: 8px; fill: #9ca3af; text-anchor: middle; }
.bar { transition: opacity 0.15s ease; cursor: pointer; }
.bar:hover { opacity: 0.75; }

.sec-chart-card { position: relative; }
.sec-tooltip {
  position: absolute; transform: translate(-50%, -110%); background: #111827; color: #fff;
  padding: 8px 10px; border-radius: 8px; font-size: 0.78rem; white-space: nowrap; pointer-events: none;
  box-shadow: 0 8px 20px rgba(0,0,0,0.25); z-index: 5;
}

/* Events table */
.sec-events-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.sec-events-head select {
  padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 0.82rem; color: #374151;
}
.sec-table-wrap { overflow-x: auto; }
.sec-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.sec-table th {
  text-align: left; color: #6b7280; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em;
  padding: 8px 10px; border-bottom: 1px solid #eef0f6; white-space: nowrap;
}
.sec-table td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; color: #111827; }
.sec-table .details { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #6b7280; }
.sec-table .nowrap { white-space: nowrap; color: #6b7280; }
.sec-table .empty { text-align: center; color: #9ca3af; padding: 20px; }

.status-pill {
  display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700;
}
.st-ok { background: #dcfce7; color: #16a34a; }
.st-warn { background: #fef3c7; color: #b45309; }
.st-critical { background: #fee2e2; color: #dc2626; }
.st-muted { background: #f3f4f6; color: #6b7280; }

@media (max-width: 768px) {
  .sec-table { font-size: 0.76rem; }
  .sec-table .details { max-width: 160px; }
}
</style>
