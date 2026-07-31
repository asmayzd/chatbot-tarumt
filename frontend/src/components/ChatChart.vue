<script setup>
import { ref, computed } from "vue";
import { jsPDF } from "jspdf";
import { t } from "../i18n.js";

const props = defineProps({
  chart: { type: Object, required: true }, // { type: 'bar'|'line', labels: string[], series: [{name, data:number[]}] }
  title: { type: String, default: "" },
});

const T = computed(() => t.value.chat);

const svgEl = ref(null);
const showTable = ref(false);
const exporting = ref(false);
const hoveredIndex = ref(null);
const tooltip = ref(null); // { left, top, label, entries: [{name, color, value}] }

// --- Reference palette (validated: node scripts/validate_palette.js) ---
// Single series -> one hue (sequential job). 2-3 series -> fixed categorical order.
const SINGLE_COLOR = "#2a78d6";
const CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a"];
const SURFACE = "#fcfcfb";

const seriesColors = computed(() => {
  const n = props.chart.series.length;
  return n > 1 ? CATEGORICAL.slice(0, n) : [SINGLE_COLOR];
});

const CHART_W = 440;
const CHART_H = 200;
const PAD_TOP = 14;
const PAD_BOTTOM = 30;
const PAD_LEFT = 10;
const PAD_RIGHT = 10;
const PLOT_W = CHART_W - PAD_LEFT - PAD_RIGHT;
const PLOT_H = CHART_H - PAD_TOP - PAD_BOTTOM;

const labels = computed(() => props.chart.labels || []);
const series = computed(() => props.chart.series || []);
const isLine = computed(() => props.chart.type === "line");

// A forecast chart is a single historical+projected series: everything from
// `forecastFrom` (the last actual point) onward renders as a dashed projection,
// same hue as the actual line — it's the same metric, not a different series.
const forecastFrom = computed(() =>
  Number.isInteger(props.chart.forecastFrom) ? props.chart.forecastFrom : null
);
const isForecast = computed(() => isLine.value && forecastFrom.value !== null);

const allValues = computed(() => series.value.flatMap((s) => s.data));
const maxV = computed(() => Math.max(0, ...allValues.value, 1));
const minV = computed(() => Math.min(0, ...allValues.value));
const span = computed(() => Math.max(1e-6, maxV.value - minV.value));

function toY(v) {
  return PAD_TOP + (1 - (v - minV.value) / span.value) * PLOT_H;
}

const yBase = computed(() => toY(0));
const hasNegative = computed(() => minV.value < 0);

const gridLines = computed(() =>
  [0, 0.5, 1].map((f) => PAD_TOP + f * PLOT_H)
);

function formatValue(v) {
  if (!Number.isFinite(v)) return "0";
  return Math.abs(v) >= 100 || Number.isInteger(v)
    ? Math.round(v).toLocaleString()
    : v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function truncate(label) {
  const str = String(label);
  return str.length > 12 ? str.slice(0, 11) + "…" : str;
}

// ---------------------------------------------------------------
// Bar layout: grouped columns, ≤24px thick, 4px rounded data-end,
// square baseline, 2px surface gap between bars in the same group.
// ---------------------------------------------------------------
const groupWidth = computed(() => (labels.value.length ? PLOT_W / labels.value.length : PLOT_W));

function roundedRectPath(x, y, w, h, { tl = 0, tr = 0, bl = 0, br = 0 }) {
  return `M${x + tl},${y}
    H${x + w - tr} A${tr},${tr} 0 0 1 ${x + w},${y + tr}
    V${y + h - br} A${br},${br} 0 0 1 ${x + w - br},${y + h}
    H${x + bl} A${bl},${bl} 0 0 1 ${x},${y + h - bl}
    V${y + tl} A${tl},${tl} 0 0 1 ${x + tl},${y} Z`.replace(/\s+/g, " ").trim();
}

function barPath(x, width, value) {
  const yVal = toY(value);
  const top = Math.min(yBase.value, yVal);
  const height = Math.max(0.001, Math.abs(yVal - yBase.value));
  const r = Math.min(4, width / 2, height);
  const corners = value >= 0 ? { tl: r, tr: r } : { bl: r, br: r };
  return roundedRectPath(x, top, width, height, corners);
}

const barGroups = computed(() => {
  if (isLine.value) return [];
  const gw = groupWidth.value;
  const gap = 2;
  const seriesCount = series.value.length;
  const availW = gw * 0.8;
  const barW = Math.min(24, (availW - gap * (seriesCount - 1)) / seriesCount);
  const totalBarsW = barW * seriesCount + gap * (seriesCount - 1);

  return labels.value.map((label, i) => {
    const groupX = PAD_LEFT + i * gw;
    const barsStartX = groupX + (gw - totalBarsW) / 2;
    const bars = series.value.map((s, j) => ({
      name: s.name,
      color: seriesColors.value[j],
      value: s.data[i],
      x: barsStartX + j * (barW + gap),
      width: barW,
      path: barPath(barsStartX + j * (barW + gap), barW, s.data[i]),
    }));
    return { label, groupX, groupWidth: gw, bars };
  });
});

function onBarGroupHover(group, i, evt) {
  hoveredIndex.value = i;
  const rect = evt.currentTarget.closest(".chatchart-svg-wrap").getBoundingClientRect();
  tooltip.value = {
    left: ((group.groupX + group.groupWidth / 2) / CHART_W) * rect.width,
    top: (PAD_TOP / CHART_H) * rect.height,
    label: group.label,
    entries: group.bars.map((b) => ({ name: b.name, color: b.color, value: b.value })),
  };
}

// ---------------------------------------------------------------
// Line layout: shared single y-scale, one crosshair, one tooltip
// listing every series at the nearest X.
// ---------------------------------------------------------------
const xStep = computed(() => (labels.value.length > 1 ? PLOT_W / (labels.value.length - 1) : PLOT_W));

function toX(i) {
  return PAD_LEFT + i * xStep.value;
}

function pathFor(coords) {
  return coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x},${c.y}`).join(" ");
}

const lineSeries = computed(() => {
  if (!isLine.value) return [];
  return series.value.map((s, j) => {
    const coords = labels.value.map((_, i) => ({ x: toX(i), y: toY(s.data[i] ?? 0) }));
    const fFrom = forecastFrom.value;
    return {
      name: s.name,
      color: seriesColors.value[j],
      data: s.data,
      coords,
      path: fFrom === null ? pathFor(coords) : "",
      solidPath: fFrom !== null ? pathFor(coords.slice(0, fFrom + 1)) : "",
      dashedPath: fFrom !== null ? pathFor(coords.slice(fFrom)) : "",
    };
  });
});

// Faint wash over the projected region so it reads as "not actuals" even
// before the reader notices the dashed stroke.
const forecastWash = computed(() => {
  if (forecastFrom.value === null) return null;
  const x = toX(forecastFrom.value);
  return { x, width: Math.max(0, CHART_W - PAD_RIGHT - x) };
});

function onLineHover(evt) {
  const wrap = evt.currentTarget.closest(".chatchart-svg-wrap");
  const rect = wrap.getBoundingClientRect();
  const relX = ((evt.clientX - rect.left) / rect.width) * CHART_W;
  const i = Math.max(0, Math.min(labels.value.length - 1, Math.round((relX - PAD_LEFT) / xStep.value)));
  hoveredIndex.value = i;
  tooltip.value = {
    left: (toX(i) / CHART_W) * rect.width,
    top: (PAD_TOP / CHART_H) * rect.height,
    label: labels.value[i],
    isForecast: forecastFrom.value !== null && i > forecastFrom.value,
    entries: lineSeries.value.map((s) => ({ name: s.name, color: s.color, value: s.data[i] ?? 0 })),
  };
}

function clearHover() {
  hoveredIndex.value = null;
  tooltip.value = null;
}

// x-axis labels: rotate + shrink once there are too many categories to sit flat
const xAxisLabels = computed(() => {
  const n = labels.value.length;
  const crowded = n > 8;
  return labels.value.map((label, i) => {
    const x = isLine.value ? toX(i) : PAD_LEFT + i * groupWidth.value + groupWidth.value / 2;
    return {
      x,
      y: CHART_H - PAD_BOTTOM + (crowded ? 10 : 14),
      text: truncate(label),
      full: String(label),
      anchor: crowded ? "end" : "middle",
      transform: crowded ? `rotate(-35 ${x} ${CHART_H - PAD_BOTTOM + 10})` : null,
    };
  });
});

// ---------------------------------------------------------------
// PDF export: rasterize the SVG (white surface) and drop it on a
// page sized to the chart, with the question as a title line.
// ---------------------------------------------------------------
async function downloadPdf() {
  if (!svgEl.value || exporting.value) return;
  exporting.value = true;
  try {
    const clone = svgEl.value.cloneNode(true);
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(CHART_W));
    clone.setAttribute("height", String(CHART_H));
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("width", String(CHART_W));
    bg.setAttribute("height", String(CHART_H));
    bg.setAttribute("fill", SURFACE);
    clone.insertBefore(bg, clone.firstChild);

    const svgString = new XMLSerializer().serializeToString(clone);
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    const dataUrl = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const scale = 2;
        const canvas = document.createElement("canvas");
        canvas.width = CHART_W * scale;
        canvas.height = CHART_H * scale;
        const ctx = canvas.getContext("2d");
        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/png"));
      };
      img.onerror = reject;
      img.src = url;
    });

    const margin = 36;
    const titleH = props.title ? 26 : 0;
    const pageW = CHART_W + margin * 2;
    const pageH = CHART_H + margin * 2 + titleH;
    const pdf = new jsPDF({
      orientation: pageW >= pageH ? "landscape" : "portrait",
      unit: "pt",
      format: [pageW, pageH],
    });

    if (props.title) {
      pdf.setFontSize(13);
      pdf.setTextColor(11, 11, 11);
      pdf.text(props.title, margin, margin);
    }
    pdf.addImage(dataUrl, "PNG", margin, margin + titleH, CHART_W, CHART_H);
    pdf.save(`chart-${Date.now()}.pdf`);
  } finally {
    exporting.value = false;
  }
}
</script>

<template>
  <div class="chatchart" @click.stop>
    <div class="chatchart-toolbar">
      <button type="button" class="cc-btn" @click="showTable = !showTable">
        {{ showTable ? T.viewAsChart : T.viewAsTable }}
      </button>
      <button type="button" class="cc-btn primary" :disabled="exporting" @click="downloadPdf">
        {{ exporting ? T.exporting : T.downloadPdf }}
      </button>
    </div>

    <div v-if="isForecast" class="chatchart-legend">
      <span class="cc-legend-item">
        <span class="cc-swatch line" :style="{ background: SINGLE_COLOR }"></span>
        {{ T.historical }}
      </span>
      <span class="cc-legend-item">
        <span class="cc-swatch line dashed"></span>
        {{ T.forecastLabel }}
      </span>
    </div>
    <div v-else-if="series.length > 1" class="chatchart-legend">
      <span v-for="s in series" :key="s.name" class="cc-legend-item">
        <span
          class="cc-swatch"
          :class="{ line: isLine }"
          :style="{ background: seriesColors[series.indexOf(s)] }"
        ></span>
        {{ s.name }}
      </span>
    </div>

    <div v-if="!showTable" class="chatchart-svg-wrap" @mouseleave="clearHover">
      <svg ref="svgEl" :viewBox="`0 0 ${CHART_W} ${CHART_H}`" class="chatchart-svg" preserveAspectRatio="xMidYMid meet">
        <line
          v-for="(gy, idx) in gridLines" :key="idx"
          :x1="PAD_LEFT" :x2="CHART_W - PAD_RIGHT" :y1="gy" :y2="gy"
          class="cc-grid"
        />
        <line
          v-if="hasNegative"
          :x1="PAD_LEFT" :x2="CHART_W - PAD_RIGHT" :y1="yBase" :y2="yBase"
          class="cc-baseline"
        />
        <rect
          v-if="forecastWash"
          :x="forecastWash.x" :y="PAD_TOP" :width="forecastWash.width" :height="PLOT_H"
          class="cc-forecast-wash"
        />

        <!-- Bar chart -->
        <template v-if="!isLine">
          <g v-for="(group, i) in barGroups" :key="group.label">
            <rect
              v-if="hoveredIndex === i"
              :x="group.groupX" :y="PAD_TOP" :width="group.groupWidth" :height="PLOT_H"
              class="cc-hover-wash"
            />
            <path v-for="b in group.bars" :key="b.name" :d="b.path" :fill="b.color" />
            <rect
              :x="group.groupX" :y="PAD_TOP" :width="group.groupWidth" :height="PLOT_H"
              class="cc-hit"
              @pointermove="onBarGroupHover(group, i, $event)"
              @pointerleave="clearHover"
            />
          </g>
        </template>

        <!-- Line chart -->
        <template v-else>
          <line
            v-if="hoveredIndex !== null"
            :x1="toX(hoveredIndex)" :x2="toX(hoveredIndex)" :y1="PAD_TOP" :y2="CHART_H - PAD_BOTTOM"
            class="cc-crosshair"
          />
          <g v-for="s in lineSeries" :key="s.name">
            <template v-if="isForecast">
              <path :d="s.solidPath" :stroke="s.color" class="cc-line" fill="none" />
              <path :d="s.dashedPath" :stroke="s.color" class="cc-line cc-line-dashed" fill="none" />
            </template>
            <path v-else :d="s.path" :stroke="s.color" class="cc-line" fill="none" />
            <circle
              v-for="(c, i) in s.coords" :key="i"
              :cx="c.x" :cy="c.y" r="2.5" :fill="s.color"
              :class="{ 'cc-dot-active': hoveredIndex === i, 'cc-dot-forecast': isForecast && i > forecastFrom }"
            />
          </g>
          <rect
            :x="PAD_LEFT" :y="PAD_TOP" :width="PLOT_W" :height="PLOT_H"
            class="cc-hit"
            @pointermove="onLineHover"
            @pointerleave="clearHover"
          />
        </template>

        <g v-for="(lbl, i) in xAxisLabels" :key="i">
          <title>{{ lbl.full }}</title>
          <text :x="lbl.x" :y="lbl.y" :text-anchor="lbl.anchor" :transform="lbl.transform" class="cc-axis-label">
            {{ lbl.text }}
          </text>
        </g>
      </svg>

      <div v-if="tooltip" class="cc-tooltip" :style="{ left: tooltip.left + 'px', top: tooltip.top + 'px' }">
        <strong>{{ tooltip.label }}<span v-if="tooltip.isForecast" class="cc-tooltip-tag"> · {{ T.forecastLabel }}</span></strong>
        <div v-for="e in tooltip.entries" :key="e.name" class="cc-tooltip-row">
          <span class="cc-key" :style="{ background: e.color }"></span>
          <span class="cc-tooltip-value">{{ formatValue(e.value) }}</span>
          <span v-if="tooltip.entries.length > 1" class="cc-tooltip-name">{{ e.name }}</span>
        </div>
      </div>
    </div>

    <div v-else class="chatchart-table-wrap">
      <table class="chatchart-table">
        <thead>
          <tr>
            <th></th>
            <th v-for="s in series" :key="s.name">{{ s.name }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(label, i) in labels" :key="label"
            :class="{ 'cc-table-forecast': isForecast && i > forecastFrom }"
          >
            <td class="cc-table-label">
              {{ label }}
              <span v-if="isForecast && i > forecastFrom" class="cc-table-tag">({{ T.forecastLabel }})</span>
            </td>
            <td v-for="s in series" :key="s.name" class="cc-table-value">{{ formatValue(s.data[i]) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.chatchart {
  margin-top: 10px;
  background: #fcfcfb;
  border: 1px solid #eef0f6;
  border-radius: 12px;
  padding: 12px 14px;
}

.chatchart-toolbar {
  display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 8px;
}
.cc-btn {
  border: 1px solid #e5e7eb; background: #fff; color: #374151;
  border-radius: 999px; padding: 5px 12px; font-size: 0.76rem; font-weight: 600; cursor: pointer;
}
.cc-btn:hover { background: #f3f4f6; }
.cc-btn.primary { background: #4f46e5; color: #fff; border-color: #4f46e5; }
.cc-btn.primary:hover { background: #4338ca; }
.cc-btn:disabled { opacity: 0.6; cursor: default; }

.chatchart-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 8px; }
.cc-legend-item { display: flex; align-items: center; gap: 6px; font-size: 0.76rem; color: #52514e; }
.cc-swatch { width: 9px; height: 9px; border-radius: 2px; display: inline-block; flex-shrink: 0; }
.cc-swatch.line { width: 12px; height: 2px; border-radius: 1px; }
.cc-swatch.line.dashed {
  background: repeating-linear-gradient(to right, #2a78d6 0, #2a78d6 3px, transparent 3px, transparent 6px);
}

.chatchart-svg-wrap { position: relative; }
.chatchart-svg { width: 100%; height: 180px; overflow: visible; display: block; }

.cc-grid { stroke: #e1e0d9; stroke-width: 1; }
.cc-baseline { stroke: #c3c2b7; stroke-width: 1; }
.cc-axis-label { font-size: 8px; fill: #898781; }
.cc-hover-wash { fill: rgba(11, 11, 11, 0.045); }
.cc-forecast-wash { fill: rgba(11, 11, 11, 0.03); }
.cc-hit { fill: transparent; cursor: pointer; }
.cc-line { stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.cc-line-dashed { stroke-dasharray: 5 4; opacity: 0.85; }
.cc-dot-active { r: 4.5; }
.cc-dot-forecast { fill-opacity: 0.55; }
.cc-crosshair { stroke: #c3c2b7; stroke-width: 1; stroke-dasharray: 3 3; }

.cc-tooltip {
  position: absolute; transform: translate(-50%, -115%); background: #0b0b0b; color: #fff;
  padding: 7px 10px; border-radius: 8px; font-size: 0.76rem; white-space: nowrap; pointer-events: none;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22); z-index: 5;
}
.cc-tooltip strong { display: block; margin-bottom: 3px; font-size: 0.74rem; opacity: 0.85; }
.cc-tooltip-tag { font-weight: 600; opacity: 0.9; }
.cc-tooltip-row { display: flex; align-items: center; gap: 6px; }
.cc-key { width: 10px; height: 2px; background: #fff; display: inline-block; flex-shrink: 0; }
.cc-tooltip-value { font-weight: 700; }
.cc-tooltip-name { opacity: 0.75; }

.chatchart-table-wrap { overflow-x: auto; }
.chatchart-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.chatchart-table th, .chatchart-table td { padding: 6px 10px; text-align: right; border-bottom: 1px solid #eef0f6; }
.chatchart-table th:first-child, .chatchart-table td:first-child { text-align: left; }
.chatchart-table th { color: #52514e; font-weight: 600; }
.cc-table-label { color: #0b0b0b; }
.cc-table-value { font-variant-numeric: tabular-nums; color: #0b0b0b; }
.cc-table-forecast td { color: #52514e; }
.cc-table-tag { font-size: 0.72rem; color: #898781; margin-left: 4px; }

@media (prefers-reduced-motion: reduce) {
  .cc-btn { transition: none; }
}
</style>
