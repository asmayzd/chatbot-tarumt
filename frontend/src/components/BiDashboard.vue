<script setup>
import { ref, onMounted, computed } from "vue";
import { api } from "../services/api.js";
import { ICONS } from "./Icons.js";
import { t } from "../i18n.js";

const T = computed(() => t.value.bi);
const C = computed(() => t.value.common);

const data = ref(null);
const loading = ref(true);
const errorMsg = ref("");

async function loadAll() {
  loading.value = true;
  errorMsg.value = "";
  try {
    data.value = await api.biOverview();
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(loadAll);

function money(v) {
  return "$" + Math.round(v).toLocaleString();
}
function num(v) {
  return Math.round(v).toLocaleString();
}
function pct(v) {
  return (v * 100).toFixed(1) + "%";
}
function days(v) {
  return v.toFixed(1) + " d";
}

// Single-hue "more sales/quantity" bars: length only, sign is never negative here.
function seqBars(points, valueKey) {
  const max = Math.max(1, ...points.map((p) => Math.abs(p[valueKey])));
  return points.map((p) => ({
    label: p.country || p.market || p.category || p.product,
    value: p[valueKey],
    widthPct: (Math.abs(p[valueKey]) / max) * 100,
  }));
}

// Two-hue "gain vs loss" bars: color encodes sign, length encodes magnitude.
function divBars(points, valueKey) {
  const max = Math.max(1, ...points.map((p) => Math.abs(p[valueKey])));
  return points.map((p) => ({
    label: p.country || p.market || p.category || p.product,
    value: p[valueKey],
    widthPct: (Math.abs(p[valueKey]) / max) * 100,
    positive: p[valueKey] >= 0,
  }));
}

const salesByCountry = computed(() => (data.value ? seqBars(data.value.sales_by_country, "sales") : []));
const salesByMarket = computed(() => (data.value ? seqBars(data.value.sales_by_market, "sales") : []));
const topProductsBySales = computed(() => (data.value ? seqBars(data.value.top_products_by_sales, "sales") : []));
const profitByCategory = computed(() => (data.value ? divBars(data.value.profit_by_category, "profit") : []));
const productsByProfit = computed(() => (data.value ? divBars(data.value.products_by_profit, "profit") : []));
const lowMarginCountries = computed(() =>
  data.value ? divBars(data.value.anomalies.low_margin_countries, "margin") : []
);
const unprofitableProducts = computed(() =>
  data.value ? divBars(data.value.anomalies.unprofitable_products, "profit") : []
);
</script>

<template>
  <div class="bi">
    <div class="bi-head">
      <h2><span class="ic" v-html="ICONS.chart"></span> {{ T.title }}</h2>
      <button class="refresh" @click="loadAll" :disabled="loading">
        {{ loading ? C.loading : C.refresh }}
      </button>
    </div>

    <p v-if="errorMsg" class="bi-error">{{ errorMsg }}</p>

    <template v-if="data">
      <!-- KPI stat tiles -->
      <div class="bi-kpis">
        <div class="bi-kpi">
          <div class="bi-kpi-ic sales" v-html="ICONS.sales"></div>
          <div class="bi-kpi-label">{{ T.totalSales }}</div>
          <div class="bi-kpi-value">{{ money(data.kpis.total_sales) }}</div>
        </div>
        <div class="bi-kpi">
          <div class="bi-kpi-ic profit" v-html="ICONS.profit"></div>
          <div class="bi-kpi-label">{{ T.totalProfit }}</div>
          <div class="bi-kpi-value">{{ money(data.kpis.total_profit) }}</div>
        </div>
        <div class="bi-kpi">
          <div class="bi-kpi-label">{{ T.totalQuantity }}</div>
          <div class="bi-kpi-value">{{ num(data.kpis.total_quantity) }}</div>
        </div>
        <div class="bi-kpi">
          <div class="bi-kpi-label">{{ T.avgDiscount }}</div>
          <div class="bi-kpi-value">{{ pct(data.kpis.average_discount) }}</div>
        </div>
        <div class="bi-kpi">
          <div class="bi-kpi-label">{{ T.avgMargin }}</div>
          <div class="bi-kpi-value">{{ pct(data.kpis.average_profit_margin) }}</div>
        </div>
        <div class="bi-kpi">
          <div class="bi-kpi-label">{{ T.avgShipping }}</div>
          <div class="bi-kpi-value">{{ days(data.kpis.average_shipping_delay) }}</div>
        </div>
      </div>

      <!-- Sequential bar charts -->
      <div class="bi-grid">
        <div class="bi-card">
          <div class="bi-card-title">{{ T.salesByCountry }}</div>
          <div class="bar-list">
            <div v-for="b in salesByCountry" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div class="bar-fill pos" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
          </div>
        </div>

        <div class="bi-card">
          <div class="bi-card-title">{{ T.salesByMarket }}</div>
          <div class="bar-list">
            <div v-for="b in salesByMarket" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div class="bar-fill pos" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
          </div>
        </div>

        <div class="bi-card">
          <div class="bi-card-title">{{ T.topProducts }}</div>
          <div class="bar-list">
            <div v-for="b in topProductsBySales" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div class="bar-fill pos" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
          </div>
        </div>

        <!-- Diverging bar charts: color encodes profit vs loss -->
        <div class="bi-card">
          <div class="bi-card-title">{{ T.profitByCategory }}</div>
          <div class="bar-legend">
            <span class="legend-item"><span class="dot pos"></span> {{ T.profit }}</span>
            <span class="legend-item"><span class="dot neg"></span> {{ T.loss }}</span>
          </div>
          <div class="bar-list">
            <div v-for="b in profitByCategory" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div :class="['bar-fill', b.positive ? 'pos' : 'neg']" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
          </div>
        </div>

        <div class="bi-card">
          <div class="bi-card-title">{{ T.bestWorstProducts }}</div>
          <div class="bar-legend">
            <span class="legend-item"><span class="dot pos"></span> {{ T.profit }}</span>
            <span class="legend-item"><span class="dot neg"></span> {{ T.loss }}</span>
          </div>
          <div class="bar-list">
            <div v-for="b in productsByProfit" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div :class="['bar-fill', b.positive ? 'pos' : 'neg']" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Anomalies -->
      <div class="bi-card-title section">
        <span class="ic warn" v-html="ICONS.anomaly"></span> {{ T.anomaliesDetected }}
      </div>
      <div class="bi-anomaly-kpis">
        <div class="bi-anomaly-kpi critical">
          <div class="bi-kpi-label">{{ T.highSalesNegProfit }}</div>
          <div class="bi-kpi-value">{{ data.anomalies.high_sales_negative_profit_count }}</div>
        </div>
        <div class="bi-anomaly-kpi critical">
          <div class="bi-kpi-label">{{ T.highDiscountNegProfit }}</div>
          <div class="bi-kpi-value">{{ data.anomalies.high_discount_negative_profit_count }}</div>
        </div>
        <div class="bi-anomaly-kpi warn">
          <div class="bi-kpi-label">{{ T.longShipping }}</div>
          <div class="bi-kpi-value">{{ data.anomalies.long_shipping_delay_count }}</div>
        </div>
        <div class="bi-anomaly-kpi warn">
          <div class="bi-kpi-label">{{ T.unusualSales }}</div>
          <div class="bi-kpi-value">{{ data.anomalies.unusual_sales_values_count }}</div>
        </div>
      </div>

      <div class="bi-grid">
        <div class="bi-card">
          <div class="bi-card-title">{{ T.leastProfitable }}</div>
          <div class="bar-list">
            <div v-for="b in unprofitableProducts" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div :class="['bar-fill', b.positive ? 'pos' : 'neg']" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ money(b.value) }}</div>
            </div>
            <p v-if="unprofitableProducts.length === 0" class="bar-empty">{{ T.noData }}</p>
          </div>
        </div>

        <div class="bi-card">
          <div class="bi-card-title">{{ T.lowestMargin }}</div>
          <div class="bar-list">
            <div v-for="b in lowMarginCountries" :key="b.label" class="bar-row">
              <div class="bar-label" :title="b.label">{{ b.label }}</div>
              <div class="bar-track">
                <div :class="['bar-fill', b.positive ? 'pos' : 'neg']" :style="{ width: b.widthPct + '%' }"></div>
              </div>
              <div class="bar-value">{{ pct(b.value) }}</div>
            </div>
            <p v-if="lowMarginCountries.length === 0" class="bar-empty">{{ T.noData }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.bi { margin: 20px 0; }
.bi-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.bi-head h2 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1.25rem; color: #111827; }
.ic { display: inline-flex; color: #4f46e5; }
.ic.warn { color: #d97706; }
.refresh {
  padding: 7px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;
  cursor: pointer; font-weight: 600; font-size: 0.85rem;
}
.refresh:hover { background: #f9fafb; }
.bi-error { color: #dc2626; background: #fef2f2; border: 1px solid #fecaca; padding: 10px 14px; border-radius: 10px; }

/* KPI tiles */
.bi-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px;
}
.bi-kpi {
  background: #fff; border: 1px solid #eef0f6; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(17, 24, 39, 0.04);
}
.bi-kpi-ic {
  width: 34px; height: 34px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center; margin-bottom: 8px;
}
.bi-kpi-ic.sales { background: #e0e7ff; color: #4f46e5; }
.bi-kpi-ic.profit { background: #dcfce7; color: #16a34a; }
.bi-kpi-label { color: #6b7280; font-size: 0.74rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.bi-kpi-value { font-size: 1.4rem; font-weight: 800; color: #111827; margin-top: 4px; word-break: break-word; }

/* Anomaly tiles: status colors carry an icon-free label, never color alone */
.bi-anomaly-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px;
}
.bi-anomaly-kpi {
  background: #fff; border: 1px solid #eef0f6; border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 4px 14px rgba(17, 24, 39, 0.04);
}
.bi-anomaly-kpi.critical .bi-kpi-value { color: #d03b3b; }
.bi-anomaly-kpi.warn .bi-kpi-value { color: #b45309; }

/* Chart cards */
.bi-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-bottom: 8px;
}
.bi-card {
  background: #fff; border: 1px solid #eef0f6; border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 4px 14px rgba(17, 24, 39, 0.04);
}
.bi-card-title { font-weight: 700; color: #111827; font-size: 0.95rem; margin-bottom: 10px; }
.bi-card-title.section { margin: 22px 0 12px; display: flex; align-items: center; gap: 8px; font-size: 1.05rem; }

.bar-legend { display: flex; gap: 16px; margin-bottom: 8px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #6b7280; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot.pos { background: #2a78d6; }
.dot.neg { background: #e34948; }

.bar-list { display: flex; flex-direction: column; gap: 8px; }
.bar-row {
  display: grid; grid-template-columns: 120px 1fr 84px; align-items: center; gap: 10px;
}
.bar-label {
  font-size: 0.8rem; color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.bar-track {
  background: #f3f4f6; border-radius: 999px; height: 12px; overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 999px; min-width: 2px; transition: width 0.3s ease;
}
.bar-fill.pos { background: #2a78d6; }
.bar-fill.neg { background: #e34948; }
.bar-value {
  font-size: 0.8rem; font-weight: 600; color: #111827; text-align: right;
  font-variant-numeric: tabular-nums;
}
.bar-empty { color: #9ca3af; font-size: 0.82rem; }

@media (max-width: 560px) {
  .bar-row { grid-template-columns: 90px 1fr 70px; gap: 6px; }
  .bar-label, .bar-value { font-size: 0.74rem; }
}
</style>
