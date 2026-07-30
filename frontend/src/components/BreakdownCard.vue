<script setup>
import { ref, computed } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "./Icons.js";
import { t } from "../i18n.js";

const props = defineProps({
  dimension: { type: String, required: true },
  title: { type: String, required: true },
  kind: { type: String, required: true }, // 'sequential' | 'diverging'
  valueFormat: { type: String, default: "money" }, // 'money' | 'plain'
  chartTypes: { type: Array, default: () => ["bar", "pie"] }, // subset of 'bar' | 'pie' | 'line'
});

const T = computed(() => t.value.bi);
const C = computed(() => t.value.common);

const chartType = ref("bar");
const panelOpen = ref(false);
const startMonth = ref("");
const endMonth = ref("");
const breakdown = ref(null); // { range, points }
const trendData = ref(null); // { range, categories, points } — only for chartType === 'line'
const loading = ref(false);
const errorMsg = ref("");

async function load() {
  loading.value = true;
  errorMsg.value = "";
  try {
    breakdown.value = await api.biBreakdown({
      dimension: props.dimension,
      start: startMonth.value || undefined,
      end: endMonth.value || undefined,
    });
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function loadTrend() {
  loading.value = true;
  errorMsg.value = "";
  try {
    trendData.value = await api.biProfitByCategoryTrend({
      start: startMonth.value || undefined,
      end: endMonth.value || undefined,
    });
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

load();

function setChartType(type) {
  chartType.value = type;
  if (type === "line" && !trendData.value) {
    loadTrend();
  }
}

function applyRange() {
  if (startMonth.value && endMonth.value && startMonth.value > endMonth.value) {
    errorMsg.value = T.value.invalidRange;
    return;
  }
  chartType.value === "line" ? loadTrend() : load();
}

function resetRange() {
  startMonth.value = "";
  endMonth.value = "";
  chartType.value === "line" ? loadTrend() : load();
}

function typeIcon(ct) {
  return ct === "bar" ? ICONS.barType : ct === "pie" ? ICONS.pieType : ICONS.lineType;
}
function typeLabel(ct) {
  return ct === "bar" ? T.value.barChartType : ct === "pie" ? T.value.pieChartType : T.value.lineChartType;
}

function formatValue(v) {
  return props.valueFormat === "money" ? "$" + Math.round(v).toLocaleString() : Math.round(v).toLocaleString();
}

// Backend points are {<label_key>: string, <value_key>: number} — same fallback
// chain the dashboard already used before this card became dimension-generic.
function normalizePoint(p) {
  return {
    label: p.country ?? p.market ?? p.category ?? p.product,
    value: p.sales ?? p.profit ?? p.margin,
  };
}

const rows = computed(() => (breakdown.value?.points || []).map(normalizePoint));

const bars = computed(() => {
  const max = Math.max(1, ...rows.value.map((r) => Math.abs(r.value)));
  return rows.value.map((r) => ({
    label: r.label,
    value: r.value,
    widthPct: (Math.abs(r.value) / max) * 100,
    positive: r.value >= 0,
  }));
});

// Categorical slots 1-3 (blue/orange/aqua) validate as an all-pairs-safe set;
// past 3 identity-carrying slices, the rest fold into a neutral "Other" slice
// rather than generating more hues (see dataviz skill: series-count ladder).
const SEQ_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"];
const OTHER_COLOR = "#898781";
const POS_COLOR = "#2a78d6";
const NEG_COLOR = "#e34948";

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function donutArcPath(cx, cy, rOuter, rInner, startAngle, endAngle) {
  const end = Math.min(endAngle, startAngle + 359.99);
  const largeArc = end - startAngle > 180 ? 1 : 0;

  const outerStart = polarToCartesian(cx, cy, rOuter, startAngle);
  const outerEnd = polarToCartesian(cx, cy, rOuter, end);
  const innerEnd = polarToCartesian(cx, cy, rInner, end);
  const innerStart = polarToCartesian(cx, cy, rInner, startAngle);

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${rInner} ${rInner} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
    "Z",
  ].join(" ");
}

const pieSlices = computed(() => {
  const r = rows.value;
  if (!r.length) return [];

  let entries;
  if (props.kind === "diverging") {
    entries = r.map((p) => ({
      label: p.label,
      rawValue: p.value,
      value: Math.abs(p.value),
      color: p.value >= 0 ? POS_COLOR : NEG_COLOR,
    }));
  } else if (r.length <= SEQ_COLORS.length) {
    entries = r.map((p, i) => ({ label: p.label, rawValue: p.value, value: Math.abs(p.value), color: SEQ_COLORS[i] }));
  } else {
    const top = r
      .slice(0, SEQ_COLORS.length)
      .map((p, i) => ({ label: p.label, rawValue: p.value, value: Math.abs(p.value), color: SEQ_COLORS[i] }));
    const restCount = r.length - SEQ_COLORS.length;
    const restTotal = r.slice(SEQ_COLORS.length).reduce((a, p) => a + Math.abs(p.value), 0);
    entries = [...top, { label: `${T.value.otherLabel} (${restCount})`, rawValue: restTotal, value: restTotal, color: OTHER_COLOR }];
  }

  const total = entries.reduce((a, e) => a + e.value, 0) || 1;
  let angle = 0;
  return entries.map((e) => {
    const start = angle;
    angle += (e.value / total) * 360;
    return { ...e, path: donutArcPath(70, 70, 62, 36, start, angle), pct: e.value / total };
  });
});

// One line per category (used only when chartType === 'line', currently profit-by-category).
const LINE_W = 400;
const LINE_H = 160;
const LINE_PAD = 20;

const multiLine = computed(() => {
  const td = trendData.value;
  if (!td || !td.points.length || !td.categories.length) return { series: [], months: [] };

  const values = td.points.flatMap((p) => td.categories.map((c) => p[c] ?? 0));
  const max = Math.max(1, ...values);
  const min = Math.min(0, ...values);
  const span = Math.max(1, max - min);
  const stepX = td.points.length > 1 ? LINE_W / (td.points.length - 1) : LINE_W;
  const toY = (v) => LINE_H - LINE_PAD - ((v - min) / span) * (LINE_H - LINE_PAD * 2);

  const series = td.categories.map((cat, i) => {
    const coords = td.points.map((p, idx) => ({
      x: idx * stepX,
      y: toY(p[cat] ?? 0),
      period: p.period,
      label: p.month_name.slice(0, 3),
    }));
    return {
      category: cat,
      color: SEQ_COLORS[i % SEQ_COLORS.length],
      coords,
      linePath: coords.map((c, idx) => `${idx === 0 ? "M" : "L"}${c.x},${c.y}`).join(" "),
    };
  });

  return { series, months: series[0]?.coords || [] };
});
</script>

<template>
  <div class="bd-card">
    <button class="bd-title" @click="panelOpen = !panelOpen" :aria-expanded="panelOpen">
      <span>{{ title }}</span>
      <span class="chevron" :class="{ open: panelOpen }">&#9662;</span>
    </button>

    <div v-if="panelOpen" class="bd-panel">
      <div class="bd-type-toggle">
        <button
          v-for="ct in chartTypes"
          :key="ct"
          type="button"
          :class="['type-btn', chartType === ct && 'active']"
          :title="typeLabel(ct)"
          @click="setChartType(ct)"
          v-html="typeIcon(ct)"
        ></button>
      </div>
      <div class="bd-range">
        <label>
          {{ T.fromMonth }}
          <input
            type="month"
            v-model="startMonth"
            :min="(breakdown || trendData)?.range?.min"
            :max="(breakdown || trendData)?.range?.max"
          />
        </label>
        <label>
          {{ T.toMonth }}
          <input
            type="month"
            v-model="endMonth"
            :min="(breakdown || trendData)?.range?.min"
            :max="(breakdown || trendData)?.range?.max"
          />
        </label>
        <button class="apply" @click="applyRange" :disabled="loading">{{ loading ? C.loading : T.applyRange }}</button>
        <button class="reset" @click="resetRange" :disabled="loading">{{ T.resetRange }}</button>
      </div>
    </div>

    <p v-if="errorMsg" class="bd-error">{{ errorMsg }}</p>

    <div v-if="kind === 'diverging'" class="bar-legend">
      <span class="legend-item"><span class="dot pos"></span>{{ T.profit }}</span>
      <span class="legend-item"><span class="dot neg"></span>{{ T.loss }}</span>
    </div>

    <div v-if="chartType === 'bar'" class="bar-list">
      <div v-for="b in bars" :key="b.label" class="bar-row">
        <div class="bar-label" :title="b.label">{{ b.label }}</div>
        <div class="bar-track">
          <div :class="['bar-fill', b.positive ? 'pos' : 'neg']" :style="{ width: b.widthPct + '%' }"></div>
        </div>
        <div class="bar-value">{{ formatValue(b.value) }}</div>
      </div>
      <p v-if="bars.length === 0" class="bar-empty">{{ T.noData }}</p>
    </div>

    <div v-else-if="chartType === 'pie'" class="pie-wrap">
      <svg viewBox="0 0 140 140" class="pie-svg">
        <path v-for="(s, i) in pieSlices" :key="i" :d="s.path" :fill="s.color" />
      </svg>
      <div class="pie-legend">
        <div v-for="(s, i) in pieSlices" :key="i" class="pie-legend-row">
          <span class="pie-dot" :style="{ background: s.color }"></span>
          <span class="pie-legend-label" :title="s.label">{{ s.label }}</span>
          <span class="pie-legend-value">{{ formatValue(s.rawValue) }} ({{ Math.round(s.pct * 100) }}%)</span>
        </div>
      </div>
      <p v-if="pieSlices.length === 0" class="bar-empty">{{ T.noData }}</p>
    </div>

    <div v-else class="line-wrap">
      <div v-if="multiLine.series.length" class="chart-legend">
        <span v-for="s in multiLine.series" :key="s.category" class="legend-item">
          <span class="swatch" :style="{ background: s.color }"></span>{{ s.category }}
        </span>
      </div>
      <svg :viewBox="`0 0 ${LINE_W} ${LINE_H}`" class="trend-svg" preserveAspectRatio="none">
        <line
          v-for="gy in [0, 0.5, 1]" :key="gy"
          :x1="0" :x2="LINE_W" :y1="LINE_H - LINE_PAD - gy * (LINE_H - LINE_PAD * 2)" :y2="LINE_H - LINE_PAD - gy * (LINE_H - LINE_PAD * 2)"
          class="grid-line"
        />
        <g v-for="s in multiLine.series" :key="s.category">
          <path :d="s.linePath" :stroke="s.color" class="multi-line" fill="none" />
          <circle v-for="c in s.coords" :key="c.period" :cx="c.x" :cy="c.y" r="2.2" :fill="s.color" />
        </g>
        <text v-for="c in multiLine.months" :key="'lbl-' + c.period" :x="c.x" :y="LINE_H - 4" class="axis-label">{{ c.label }}</text>
      </svg>
      <p v-if="!multiLine.series.length" class="bar-empty">{{ T.noData }}</p>
    </div>
  </div>
</template>

<style scoped>
.bd-card {
  background: #fff; border: 1px solid #eef0f6; border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 4px 14px rgba(17, 24, 39, 0.04);
}
.bd-title {
  display: flex; align-items: center; justify-content: space-between; width: 100%;
  background: none; border: none; padding: 0; margin-bottom: 10px; cursor: pointer;
  font-weight: 700; color: #111827; font-size: 0.95rem; font-family: inherit; text-align: left;
}
.chevron { color: #9ca3af; transition: transform 0.15s ease; font-size: 0.8rem; }
.chevron.open { transform: rotate(180deg); }

.bd-panel {
  display: flex; flex-wrap: wrap; align-items: end; gap: 12px;
  background: #f9fafb; border: 1px solid #eef0f6; border-radius: 12px; padding: 10px 12px; margin-bottom: 12px;
}
.bd-type-toggle { display: flex; gap: 4px; }
.type-btn {
  display: flex; align-items: center; justify-content: center; width: 32px; height: 32px;
  border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; color: #6b7280; cursor: pointer;
}
.type-btn.active { background: #4f46e5; border-color: #4f46e5; color: #fff; }
.bd-range { display: flex; align-items: end; gap: 8px; flex-wrap: wrap; }
.bd-range label { display: flex; flex-direction: column; gap: 4px; font-size: 0.74rem; color: #6b7280; font-weight: 600; }
.bd-range input[type="month"] {
  padding: 5px 8px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 0.8rem; color: #374151;
}
.apply, .reset {
  padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;
  cursor: pointer; font-weight: 600; font-size: 0.8rem; height: fit-content;
}
.apply:hover, .reset:hover { background: #f3f4f6; }
.apply:disabled, .reset:disabled { opacity: 0.6; cursor: default; }
.bd-error {
  color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; padding: 8px 12px;
  border-radius: 10px; margin-bottom: 10px; font-size: 0.82rem;
}

.bar-legend { display: flex; gap: 16px; margin-bottom: 8px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #6b7280; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot.pos { background: #2a78d6; }
.dot.neg { background: #e34948; }

.bar-list { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: grid; grid-template-columns: 120px 1fr 84px; align-items: center; gap: 10px; }
.bar-label { font-size: 0.8rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { background: #f3f4f6; border-radius: 999px; height: 12px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 999px; min-width: 2px; transition: width 0.3s ease; }
.bar-fill.pos { background: #2a78d6; }
.bar-fill.neg { background: #e34948; }
.bar-value { font-size: 0.8rem; font-weight: 600; color: #111827; text-align: right; font-variant-numeric: tabular-nums; }
.bar-empty { color: #9ca3af; font-size: 0.82rem; }

.pie-wrap { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.pie-svg { width: 140px; height: 140px; flex-shrink: 0; }
.pie-legend { display: flex; flex-direction: column; gap: 7px; flex: 1; min-width: 160px; }
.pie-legend-row { display: flex; align-items: center; gap: 8px; font-size: 0.8rem; }
.pie-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.pie-legend-label { color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.pie-legend-value { color: #111827; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }

.chart-legend { display: flex; gap: 14px; margin-bottom: 8px; flex-wrap: wrap; }
.chart-legend .legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.76rem; color: #6b7280; }
.chart-legend .swatch { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }

.trend-svg { width: 100%; height: 170px; overflow: visible; }
.grid-line { stroke: #f0f1f5; stroke-width: 1; }
.axis-label { font-size: 8px; fill: #9ca3af; text-anchor: middle; }
.multi-line { stroke-width: 2; }

@media (max-width: 560px) {
  .bar-row { grid-template-columns: 90px 1fr 70px; gap: 6px; }
  .bar-label, .bar-value { font-size: 0.74rem; }
}
</style>
