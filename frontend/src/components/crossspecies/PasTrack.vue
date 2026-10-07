<template>
  <div class="pas-row" :class="{ 'pas-row--dense': dense }">
    <div class="pas-row-label">
      <router-link v-if="to" :to="to" class="pas-row-title pas-row-title--link" :title="label">
        {{ label }}
      </router-link>
      <span v-else class="pas-row-title" :title="label">{{ label }}</span>
      <span v-if="sublabel" class="pas-row-sub">{{ sublabel }}</span>
    </div>

    <div class="pas-row-track">
      <div class="pas-baseline"></div>
      <!--
        The distal PA site is the anchor every distance on this row is measured
        from, so it is drawn rather than left implicit at the axis edge.
      -->
      <div v-if="points.length" class="pas-distal" :title="distalTitle"></div>
      <div
        v-for="mark in marks"
        :key="mark.key"
        class="pas-anchor"
        :style="{ left: `${mark.point.x * 100}%` }"
        @mouseenter="openMark(mark.key, $event)"
        @mouseleave="closeMark(mark.key, $event)"
      >
        <button
          class="pas-mark"
          :class="[`pas-mark--${mark.point.levelKey}`, { 'pas-mark--muted': mark.point.muted }]"
          :style="markStyle(mark.point)"
          type="button"
          :aria-label="mark.ariaLabel"
          :aria-expanded="pinnedKey === mark.key"
          :aria-describedby="openKey === mark.key ? mark.tipId : undefined"
          @click="togglePin(mark.key, $event)"
          @focus="openMark(mark.key, $event)"
          @blur="closeMark(mark.key)"
        ></button>
        <span class="pas-stem" :style="{ height: `${stemHeight(mark.point)}px` }"></span>
        <div
          v-if="openKey === mark.key"
          :id="mark.tipId"
          class="pas-tip"
          :style="{ left: `${tipOffset}px` }"
          role="tooltip"
        >
          <div class="pas-tip-kicker">PA Site · P{{ mark.point.order }}</div>
          <div class="pas-tip-head">{{ mark.point.key }}</div>
          <dl class="pas-tip-body">
            <template v-for="row in mark.rows" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd :class="{ 'pas-tip-usage': row.label.toLowerCase().includes('usage') }">{{ row.value }}</dd>
            </template>
          </dl>
        </div>
      </div>
      <span v-if="!points.length" class="pas-row-empty">{{ emptyMessage }}</span>
    </div>

    <div class="pas-row-meta" :title="metaTitle || undefined">{{ meta }}</div>
  </div>
</template>

<script>
/*
 * Module scope: a `<script setup>` body runs once per instance, so a counter
 * declared there could not hand out document-unique tooltip ids.
 */
let trackInstanceCount = 0
const nextTrackInstanceId = () => `pas-track-${(trackInstanceCount += 1)}`
</script>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { formatCount, formatDistance, formatUsage } from '@/utils/pasLayout'

const props = defineProps({
  label: { type: String, required: true },
  sublabel: { type: String, default: '' },
  meta: { type: String, default: '' },
  metaTitle: { type: String, default: '' },
  to: { type: [Object, String], default: null },
  points: { type: Array, default: () => [] },
  usageLabel: { type: String, default: 'Relative usage' },
  sampleKey: { type: String, default: '' },
  dense: { type: Boolean, default: false },
  emptyMessage: { type: String, default: 'No transcript-linked PA sites available.' }
})

const instanceId = nextTrackInstanceId()

const distalTitle = 'Distal PA site — every distance on this row is measured upstream of here'

const laneStep = () => (props.dense ? 10 : 13)

const stemHeight = point => point.lane * laneStep() + 4

const markStyle = point => ({
  width: `${point.radius * 2}px`,
  height: `${point.radius * 2}px`,
  bottom: `${stemHeight(point) - point.radius}px`
})

const tooltipRows = point => {
  const site = point.site || {}
  const cluster =
    site.cluster_start != null && site.cluster_end != null
      ? `${site.cluster_start}–${site.cluster_end}`
      : 'not available'
  return [
    { label: 'Upstream of distal', value: formatDistance(point.distance) },
    { label: 'Position', value: site.position ?? 'not available' },
    { label: 'Cluster', value: cluster },
    { label: 'PAS motif', value: site.pas_type === 'not_assessed' ? 'Not assessed' : (site.pas_motif || (site.pas_type ? 'No motif' : 'Not recorded')) },
    { label: 'Evidence level', value: site.pa_level || 'Not assigned' },
    { label: props.sampleKey ? props.usageLabel : `Mean ${props.usageLabel.toLowerCase()}`, value: formatUsage(point.usage) },
    { label: props.sampleKey ? 'Supporting reads' : 'Total supporting reads', value: point.supportingReads != null ? formatCount(point.supportingReads) : 'Not available' },
    ...(!props.sampleKey ? [{ label: 'Supporting groups', value: formatCount(site.sample_count) }] : [])
  ]
}

/*
 * Site ids can repeat across the points of one row (and certainly across
 * rows), so the render key and the tooltip id both carry the index.
 */
const marks = computed(() =>
  props.points.map((point, index) => {
    const rows = tooltipRows(point)
    return {
      point,
      rows,
      key: `${index}:${point.key}`,
      tipId: `${instanceId}-tip-${index}`,
      ariaLabel: `PA site P${point.order} ${point.key}. ${rows
        .map(row => `${row.label}: ${row.value}`)
        .join('. ')}.`
    }
  })
)

/*
 * Tooltip visibility is driven from script rather than :hover so the hover
 * content can satisfy WCAG 1.4.13: it stays open while the pointer is over it
 * (the panel overlaps its own mark, so there is no gap to cross), a click pins
 * it open, and Escape dismisses it without moving the pointer.
 */
const openKey = ref(null)
const pinnedKey = ref(null)
const tipOffset = ref(0)

const openMark = (key, event) => {
  if (pinnedKey.value && pinnedKey.value !== key) pinnedKey.value = null
  const anchor = event?.currentTarget?.closest('.pas-anchor')
  if (anchor) {
    const left = anchor.getBoundingClientRect().left
    const width = Math.min(280, window.innerWidth - 48)
    tipOffset.value = Math.min(Math.max(left - width / 2, 12), window.innerWidth - width - 12) - left
  }
  openKey.value = key
}

const closeMark = (key, event) => {
  if (pinnedKey.value === key) return
  // The pointer may leave a mark the keyboard is still focused on.
  const anchor = event?.currentTarget
  if (anchor?.contains?.(document.activeElement)) return
  if (openKey.value === key) openKey.value = null
}

const togglePin = (key, event) => {
  if (pinnedKey.value === key) {
    pinnedKey.value = null
    openKey.value = null
    return
  }
  pinnedKey.value = key
  openMark(key, event)
}

const dismiss = () => {
  pinnedKey.value = null
  openKey.value = null
}

const onDocumentKeydown = event => {
  if (event.key === 'Escape') dismiss()
}

const stopKeyListener = () => {
  if (typeof document === 'undefined') return
  document.removeEventListener('keydown', onDocumentKeydown)
  window.removeEventListener('resize', dismiss)
}

watch(openKey, key => {
  if (typeof document === 'undefined') return
  stopKeyListener()
  if (key) {
    document.addEventListener('keydown', onDocumentKeydown)
    window.addEventListener('resize', dismiss)
  }
})
watch(() => props.points, dismiss)

onBeforeUnmount(stopKeyListener)
</script>

<style scoped>
/*
 * The column template must stay identical to .pas-axis in
 * PasArchitecturePanel.vue at every breakpoint, otherwise the ticks stop
 * marking the positions the marks are drawn at. Fallbacks keep the row usable
 * if the component is ever mounted outside that panel.
 */
.pas-row {
  display: grid;
  grid-template-columns: var(--pas-gutter, 190px) 1fr var(--pas-meta, 96px);
  align-items: end;
  gap: 0 14px;
  padding: 10px 0;
}
.pas-row--dense { padding: 4px 0; }

.pas-row-label { min-width: 0; padding-bottom: 2px; }
.pas-row-title {
  display: block;
  overflow: hidden;
  color: var(--aa-slate-800, #1e293b);
  font-size: 0.95rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pas-row--dense .pas-row-title {
  font-family: var(--aa-font-sans);
  font-size: 0.86rem;
  font-weight: 600;
}
.pas-row-title--link { color: var(--aa-teal-700, #0d7377); text-decoration: none; }
.pas-row-title--link:hover { color: var(--aa-teal-800, #0a5c5f); text-decoration: underline; text-underline-offset: 3px; }
.pas-row-sub {
  display: block;
  overflow: hidden;
  color: var(--aa-slate-500, #64748b);
  font-size: 0.82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pas-row--dense .pas-row-sub { font-size: 0.78rem; font-style: normal; }

.pas-row-track {
  position: relative;
  height: var(--pas-track-height, 58px);
}
.pas-row--dense .pas-row-track { height: var(--pas-track-height-dense, 44px); }

.pas-baseline {
  position: absolute;
  right: 0;
  bottom: 3px;
  left: 0;
  height: 2px;
  border-radius: 2px;
  background: var(--aa-slate-200, #e2e8f0);
}

/*
 * The anchor line sits at the right edge, where axisFraction places distance 0.
 * Every mark on the row reads as "this far upstream of that line".
 */
.pas-distal {
  position: absolute;
  right: 0;
  bottom: 3px;
  width: 2px;
  height: 18px;
  border-radius: 1px;
  background: var(--aa-teal-700, #0d7377);
  opacity: 0.35;
}
.pas-row--dense .pas-distal { height: 13px; }

.pas-anchor { position: absolute; bottom: 0; width: 0; }

.pas-stem {
  position: absolute;
  bottom: 3px;
  left: 0;
  width: 1px;
  background: var(--aa-slate-300, #cbd5e1);
  transform: translateX(-50%);
  pointer-events: none;
}

.pas-mark {
  position: absolute;
  left: 0;
  padding: 0;
  border: 2px solid var(--pas-mark-border, #ffffff);
  border-style: var(--pas-mark-border-style, solid);
  border-radius: 50%;
  background: var(--pas-mark-fill, var(--pas-level-color, var(--aa-slate-500, #64748b)));
  box-shadow: var(--pas-mark-shadow, 0 0 0 1px rgba(15, 23, 42, 0.14));
  cursor: pointer;
  transform: translateX(-50%);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.pas-mark:hover,
.pas-mark:focus-visible {
  box-shadow: 0 0 0 4px rgba(13, 115, 119, 0.16);
  outline: none;
  transform: translateX(-50%) scale(1.15);
}
.pas-mark--l1 { --pas-level-color: var(--pas-l1, #0d7377); }
.pas-mark--l2 { --pas-level-color: var(--pas-l2, #d3a05c); }
.pas-mark--l3 { --pas-level-color: var(--pas-l3, #8c89b0); }

/*
 * Dashed ring = "no PAS level assigned", and nothing else. The tinted fill
 * keeps a *measured* unassigned site distinct from the hollow, white-filled
 * "not detected" state below.
 */
.pas-mark--unassigned {
  --pas-level-color: var(--aa-slate-300, #cbd5e1);
  --pas-mark-fill: var(--aa-slate-100, #f1f5f9);
  --pas-mark-border: var(--pas-level-color);
  --pas-mark-border-style: dashed;
  --pas-mark-shadow: none;
}

/*
 * "Not detected in this context": buildTrackPoints reports usage === null when
 * the selected sample never measured the site (or no sample supports it),
 * which is a different claim from "measured at zero". The mark goes hollow but
 * keeps its level colour as a solid border, so evidence level stays readable and a
 * muted L1 never looks like a muted L3 or like an unassigned site.
 */
.pas-mark--muted {
  --pas-mark-fill: #ffffff;
  --pas-mark-border: var(--pas-level-color, var(--aa-slate-500, #64748b));
  --pas-mark-shadow: 0 0 0 1px rgba(15, 23, 42, 0.06);
}

.pas-tip {
  position: absolute;
  bottom: calc(100% + 6px);
  z-index: 20;
  width: 280px;
  max-width: calc(100vw - 48px);
  padding: 13px 15px;
  border: 1px solid rgba(13, 115, 119, 0.20);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  box-shadow: 0 8px 32px rgba(13, 115, 119, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.9);
  color: #0f172a;
  font-family: var(--aa-font-sans);
  font-size: 13px;
  animation: pas-tip-in 0.12s ease;
}

@keyframes pas-tip-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.pas-tip-kicker {
  margin-bottom: 3px;
  color: #0d7377;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.pas-tip-head {
  margin-bottom: 9px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(13, 115, 119, 0.15);
  color: #0f172a;
  font-family: var(--aa-font-sans);
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1.5;
  word-break: break-all;
}
.pas-tip-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  align-items: center;
  margin: 0;
  font-size: 12.5px;
}
.pas-tip-body dt { color: #475569; }
.pas-tip-body dd {
  margin: 0;
  color: #0f172a;
  font-weight: 600;
  font-family: var(--aa-font-sans);
  font-variant-numeric: tabular-nums;
  text-align: left;
  word-break: break-all;
}
.pas-tip-body dd.pas-tip-usage { color: #0d7377; font-weight: 700; }

.pas-row-empty {
  position: absolute;
  bottom: 10px;
  left: 0;
  color: var(--aa-slate-500, #64748b);
  font-size: 0.76rem;
}

.pas-row-meta {
  padding-bottom: 4px;
  color: var(--aa-slate-500, #64748b);
  font-family: var(--aa-font-sans);
  font-size: 0.79rem;
  text-align: right;
  white-space: nowrap;
}

@media (max-width: 640px) {
  /*
   * The row stacks into one full-width column here. PasArchitecturePanel
   * collapses .pas-axis to a single full-width column at the same breakpoint
   * so the scale keeps spanning exactly this track column.
   */
  .pas-row { grid-template-columns: 1fr; gap: 6px; }
  .pas-row-meta { text-align: left; }
  .pas-row--dense { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; align-items: center; }
  .pas-row--dense .pas-row-label { grid-column: 1; grid-row: 1; }
  .pas-row--dense .pas-row-meta { grid-column: 2; grid-row: 1; text-align: right; padding-bottom: 0; }
  .pas-row--dense .pas-row-track { grid-column: 1 / -1; grid-row: 2; }
}
</style>
