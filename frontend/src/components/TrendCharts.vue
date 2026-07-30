<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { api } from "../services/api.js";
import { t, lang } from "../i18n.js";

const T = computed(() => t.value.bi);
const C = computed(() => t.value.common);

const trendData = ref(null); // { range: {min, max}, points, insights }
const startMonth = ref("");
const endMonth = ref("");
const loading = ref(false);
const errorMsg = ref("");
const hovered = ref(null); // { metric, point, cx, cy }

async function load() {
  loading.value = true;
  errorMsg.value = "";
  try {
    trendData.value = await api.biMonthlyTrends({
      start: startMonth.value || undefined,
      end: endMonth.value || undefined,
      lang: lang.value,
    });
    if (!startMonth.value && !endMonth.value && trendData.value.range.min) {
      startMonth.value = trendData.value.range.min;
      endMonth.value = trendData.value.range.max;
    }
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(lang, load);

function applyRange() {
  if (startMonth.value && endMonth.value && startMonth.value > endMonth.value) {
    errorMsg.value = T.value.invalidRange;
    return;
  }
  load();
}

const CHART_W = 560;
const CHART_H = 160;
const PAD_Y = 20;

// Ordinary least-squares slope/intercept over arbitrary (x, y) pairs, for the dashed trend line.
function linearRegression(pairs) {
  const n = pairs.length;
  const meanX = pairs.reduce((a, [x]) => a + x, 0) / n;
  const meanY = pairs.reduce((a, [, y]) => a + y, 0) / n;
  let num = 0;
  let den = 0;
  pairs.forEach(([x, y]) => {
    num += (x - meanX) * (y - meanY);
    den += (x - meanX) ** 2;
  });
  const slope = den === 0 ? 0 : num / den;
  const intercept = meanY - slope * meanX;
  return { slope, intercept };
}

// Tukey's IQR fences (1.5x). Needs at least 4 points to be meaningful.
function detectOutliers(values) {
  const n = values.length;
  if (n < 4) return values.map(() => false);

  const sorted = [...values].sort((a, b) => a - b);
  const quantile = (q) => {
    const pos = (sorted.length - 1) * q;
    const base = Math.floor(pos);
    const rest = pos - base;
    return base + 1 < sorted.length ? sorted[base] + rest * (sorted[base + 1] - sorted[base]) : sorted[base];
  };
  const q1 = quantile(0.25);
  const q3 = quantile(0.75);
  const iqr = q3 - q1;
  const lower = q1 - 1.5 * iqr;
  const upper = q3 + 1.5 * iqr;
  return values.map((v) => v < lower || v > upper);
}

function buildLineSeries(points, valueKey) {
  if (!points.length) return { coords: [], linePath: "", trendPath: "" };

  const values = points.map((p) => p[valueKey]);
  const max = Math.max(1, ...values);
  const min = Math.min(0, ...values);
  const span = Math.max(1, max - min);
  const stepX = points.length > 1 ? CHART_W / (points.length - 1) : CHART_W;
  const toY = (v) => CHART_H - PAD_Y - ((v - min) / span) * (CHART_H - PAD_Y * 2);
  const outlierFlags = detectOutliers(values);

  const coords = points.map((p, i) => ({
    x: i * stepX,
    y: toY(p[valueKey]),
    label: p.month_name.slice(0, 3),
    value: p[valueKey],
    period: p.period,
    isOutlier: outlierFlags[i],
  }));

  // Fit the trend line on non-outlier months only, so one anomalous month
  // doesn't tilt the whole regression, but still draw it across the full width.
  const regressionPairs = values.map((v, i) => [i, v]).filter((_, i) => !outlierFlags[i]);
  let trendPath = "";
  if (regressionPairs.length > 1) {
    const { slope, intercept } = linearRegression(regressionPairs);
    const startY = toY(intercept);
    const endY = toY(intercept + slope * (points.length - 1));
    trendPath = `M0,${startY} L${CHART_W},${endY}`;
  }

  return {
    coords,
    linePath: coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`).join(" "),
    trendPath,
    hasOutliers: outlierFlags.some(Boolean),
  };
}

const points = computed(() => trendData.value?.points || []);
const salesSeries = computed(() => buildLineSeries(points.value, "sales"));
const profitSeries = computed(() => buildLineSeries(points.value, "profit"));
const ordersSeries = computed(() => buildLineSeries(points.value, "order_count"));

function showTooltip(metric, coord, evt) {
  const rect = evt.currentTarget.closest("svg").getBoundingClientRect();
  hovered.value = { metric, ...coord, cx: evt.clientX - rect.left, cy: evt.clientY - rect.top };
}
function hideTooltip() {
  hovered.value = null;
}

function money(v) {
  return "$" + Math.round(v).toLocaleString();
}
function num(v) {
  return Math.round(v).toLocaleString();
}
</script>

<template>
  <div v-if="trendData" class="trends">
    <div class="trends-head">
      <div class="trends-title">{{ T.trendsTitle }}</div>
      <div class="trends-filters">
        <label>
          {{ T.fromMonth }}
          <input
            type="month"
            v-model="startMonth"
            :min="trendData.range.min"
            :max="trendData.range.max"
          />
        </label>
        <label>
          {{ T.toMonth }}
          <input
            type="month"
            v-model="endMonth"
            :min="trendData.range.min"
            :max="trendData.range.max"
          />
        </label>
        <button class="apply" @click="applyRange" :disabled="loading">
          {{ loading ? C.loading : T.applyRange }}
        </button>
      </div>
    </div>

    <p v-if="errorMsg" class="trends-error">{{ errorMsg }}</p>

    <div class="trends-grid">
      <div class="trend-card">
        <div class="bi-card-title">{{ T.salesTrend }}</div>
        <div v-if="salesSeries.trendPath" class="chart-legend">
          <span class="legend-item"><span class="swatch line sales"></span>{{ T.actualLabel }}</span>
          <span class="legend-item"><span class="swatch dash"></span>{{ T.trendLabel }}</span>
          <span v-if="salesSeries.hasOutliers" class="legend-item"><span class="swatch dot-swatch outlier"></span>{{ T.outlierLabel }}</span>
        </div>
        <svg :viewBox="`0 0 ${CHART_W} ${CHART_H}`" class="trend-svg" preserveAspectRatio="none">
          <line
            v-for="gy in [0, 0.5, 1]" :key="gy"
            :x1="0" :x2="CHART_W" :y1="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)" :y2="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)"
            class="grid-line"
          />
          <path v-if="salesSeries.trendPath" :d="salesSeries.trendPath" class="trend-dash" fill="none" />
          <path :d="salesSeries.linePath" class="trend-line sales" fill="none" />
          <g v-for="c in salesSeries.coords" :key="c.period">
            <circle v-if="c.isOutlier" :cx="c.x" :cy="c.y" r="6" class="outlier-ring" />
            <circle :cx="c.x" :cy="c.y" r="7" class="hit" @mousemove="showTooltip('sales', c, $event)" @mouseleave="hideTooltip" />
            <circle :cx="c.x" :cy="c.y" r="2.5" :class="['dot', c.isOutlier ? 'outlier' : 'sales']" />
            <text :x="c.x" :y="CHART_H - 4" class="axis-label">{{ c.label }}</text>
          </g>
        </svg>
        <p v-if="trendData.insights.sales" class="trend-insight">{{ trendData.insights.sales }}</p>
        <p v-else class="trend-insight muted">
          {{ points.length < 2 ? T.notEnoughData : T.insightUnavailable }}
        </p>
      </div>

      <div class="trend-card">
        <div class="bi-card-title">{{ T.profitTrend }}</div>
        <div v-if="profitSeries.trendPath" class="chart-legend">
          <span class="legend-item"><span class="swatch line profit"></span>{{ T.actualLabel }}</span>
          <span class="legend-item"><span class="swatch dash"></span>{{ T.trendLabel }}</span>
          <span v-if="profitSeries.hasOutliers" class="legend-item"><span class="swatch dot-swatch outlier"></span>{{ T.outlierLabel }}</span>
        </div>
        <svg :viewBox="`0 0 ${CHART_W} ${CHART_H}`" class="trend-svg" preserveAspectRatio="none">
          <line
            v-for="gy in [0, 0.5, 1]" :key="gy"
            :x1="0" :x2="CHART_W" :y1="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)" :y2="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)"
            class="grid-line"
          />
          <path v-if="profitSeries.trendPath" :d="profitSeries.trendPath" class="trend-dash" fill="none" />
          <path :d="profitSeries.linePath" class="trend-line profit" fill="none" />
          <g v-for="c in profitSeries.coords" :key="c.period">
            <circle v-if="c.isOutlier" :cx="c.x" :cy="c.y" r="6" class="outlier-ring" />
            <circle :cx="c.x" :cy="c.y" r="7" class="hit" @mousemove="showTooltip('profit', c, $event)" @mouseleave="hideTooltip" />
            <circle :cx="c.x" :cy="c.y" r="2.5" :class="['dot', c.isOutlier ? 'outlier' : 'profit']" />
            <text :x="c.x" :y="CHART_H - 4" class="axis-label">{{ c.label }}</text>
          </g>
        </svg>
        <p v-if="trendData.insights.profit" class="trend-insight">{{ trendData.insights.profit }}</p>
        <p v-else class="trend-insight muted">
          {{ points.length < 2 ? T.notEnoughData : T.insightUnavailable }}
        </p>
      </div>

      <div class="trend-card">
        <div class="bi-card-title">{{ T.ordersTrend }}</div>
        <div v-if="ordersSeries.trendPath" class="chart-legend">
          <span class="legend-item"><span class="swatch line orders"></span>{{ T.actualLabel }}</span>
          <span class="legend-item"><span class="swatch dash"></span>{{ T.trendLabel }}</span>
          <span v-if="ordersSeries.hasOutliers" class="legend-item"><span class="swatch dot-swatch outlier"></span>{{ T.outlierLabel }}</span>
        </div>
        <svg :viewBox="`0 0 ${CHART_W} ${CHART_H}`" class="trend-svg" preserveAspectRatio="none">
          <line
            v-for="gy in [0, 0.5, 1]" :key="gy"
            :x1="0" :x2="CHART_W" :y1="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)" :y2="CHART_H - PAD_Y - gy * (CHART_H - PAD_Y * 2)"
            class="grid-line"
          />
          <path v-if="ordersSeries.trendPath" :d="ordersSeries.trendPath" class="trend-dash" fill="none" />
          <path :d="ordersSeries.linePath" class="trend-line orders" fill="none" />
          <g v-for="c in ordersSeries.coords" :key="c.period">
            <circle v-if="c.isOutlier" :cx="c.x" :cy="c.y" r="6" class="outlier-ring" />
            <circle :cx="c.x" :cy="c.y" r="7" class="hit" @mousemove="showTooltip('orders', c, $event)" @mouseleave="hideTooltip" />
            <circle :cx="c.x" :cy="c.y" r="2.5" :class="['dot', c.isOutlier ? 'outlier' : 'orders']" />
            <text :x="c.x" :y="CHART_H - 4" class="axis-label">{{ c.label }}</text>
          </g>
        </svg>
        <p v-if="trendData.insights.orders" class="trend-insight">{{ trendData.insights.orders }}</p>
        <p v-else class="trend-insight muted">
          {{ points.length < 2 ? T.notEnoughData : T.insightUnavailable }}
        </p>
      </div>
    </div>

    <div
      v-if="hovered"
      class="trend-tooltip"
      :style="{ left: hovered.cx + 'px', top: hovered.cy + 'px' }"
    >
      <strong>{{ hovered.period }}</strong>
      <div>{{ hovered.metric === "sales" ? money(hovered.value) : hovered.metric === "profit" ? money(hovered.value) : num(hovered.value) }}</div>
      <div v-if="hovered.isOutlier" class="tooltip-outlier">{{ T.outlierLabel }}</div>
    </div>
  </div>
</template>

<style scoped>
.trends { margin-bottom: 20px; position: relative; }
.trends-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }
.trends-title { font-weight: 700; color: #111827; font-size: 1.05rem; }
.trends-filters { display: flex; align-items: end; gap: 10px; flex-wrap: wrap; }
.trends-filters label { display: flex; flex-direction: column; gap: 4px; font-size: 0.76rem; color: #6b7280; font-weight: 600; }
.trends-filters input[type="month"] {
  padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 0.82rem; color: #374151;
}
.apply {
  padding: 7px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;
  cursor: pointer; font-weight: 600; font-size: 0.85rem; height: fit-content;
}
.apply:hover { background: #f9fafb; }
.apply:disabled { opacity: 0.6; cursor: default; }
.trends-error { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; padding: 8px 14px; border-radius: 10px; margin-bottom: 10px; font-size: 0.85rem; }

.trends-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
.trend-card {
  background: #fff; border: 1px solid #eef0f6; border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 4px 14px rgba(17, 24, 39, 0.04); position: relative;
}
.bi-card-title { font-weight: 700; color: #111827; font-size: 0.95rem; margin-bottom: 10px; }

.chart-legend { display: flex; gap: 14px; margin-bottom: 8px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.76rem; color: #6b7280; }
.swatch { width: 16px; height: 2px; display: inline-block; border-radius: 1px; }
.swatch.line.sales { background: #2a78d6; }
.swatch.line.profit { background: #16a34a; }
.swatch.line.orders { background: #d97706; }
.swatch.dash {
  background: repeating-linear-gradient(to right, #9ca3af 0, #9ca3af 4px, transparent 4px, transparent 8px);
}
.swatch.dot-swatch { width: 8px; height: 8px; border-radius: 50%; }
.swatch.dot-swatch.outlier { background: #dc2626; }

.trend-svg { width: 100%; height: 170px; overflow: visible; }
.grid-line { stroke: #f0f1f5; stroke-width: 1; }
.axis-label { font-size: 8px; fill: #9ca3af; text-anchor: middle; }

.trend-line { stroke-width: 2; }
.trend-line.sales { stroke: #2a78d6; }
.trend-line.profit { stroke: #16a34a; }
.trend-line.orders { stroke: #d97706; }

.trend-dash { stroke: #9ca3af; stroke-width: 1.5; stroke-dasharray: 5 4; opacity: 0.85; }

.dot { pointer-events: none; }
.dot.sales { fill: #2a78d6; }
.dot.profit { fill: #16a34a; }
.dot.orders { fill: #d97706; }
.dot.outlier { fill: #dc2626; }
.outlier-ring { fill: none; stroke: #dc2626; stroke-width: 1.5; opacity: 0.6; pointer-events: none; }
.hit { fill: transparent; cursor: pointer; }

.trend-insight { margin-top: 10px; font-size: 0.85rem; color: #374151; line-height: 1.4; }
.trend-insight.muted { color: #9ca3af; font-style: italic; }

.trend-tooltip {
  position: absolute; transform: translate(-50%, -110%); background: #111827; color: #fff;
  padding: 8px 10px; border-radius: 8px; font-size: 0.78rem; white-space: nowrap; pointer-events: none;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25); z-index: 5;
}
.tooltip-outlier { color: #fca5a5; font-weight: 600; margin-top: 2px; }

@media (max-width: 560px) {
  .trends-filters { width: 100%; }
}
</style>
