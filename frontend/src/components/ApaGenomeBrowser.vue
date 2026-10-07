<template>
  <div class="apa-genome-browser" :class="{ 'apa-genome-browser--touch': isTouchLayout }">
    <!-- Controls -->
    <div class="browser-controls">
      <v-btn-group v-if="!isTouchLayout" density="compact" variant="outlined">
        <v-btn size="small" @click="zoomIn" title="Zoom In">
          <v-icon>mdi-magnify-plus</v-icon>
        </v-btn>
        <v-btn size="small" @click="zoomOut" title="Zoom Out">
          <v-icon>mdi-magnify-minus</v-icon>
        </v-btn>
        <v-btn size="small" @click="resetZoom" title="Reset View">
          <v-icon>mdi-fit-to-screen</v-icon>
        </v-btn>
      </v-btn-group>
      <span class="browser-gesture-hint text-caption text-grey">
        <v-icon size="x-small" class="mr-1">mdi-gesture-pinch</v-icon>
        {{ isTouchLayout ? 'Swipe horizontally to inspect the full genome browser track' : 'Wheel to zoom • drag to pan' }}
      </span>

      <!-- Sample selectors — pushed to right -->
      <div class="sample-selectors ml-auto">
        <!-- Tissue selector -->
        <v-menu
          v-model="tissueMenuOpen"
          :close-on-content-click="false"
          max-height="360"
          :width="tissueMenuWidth"
          @update:model-value="onTissueMenuToggle"
        >
          <template #activator="{ props: menuProps }">
            <div
              v-bind="menuProps"
              ref="tissueBtnRef"
              class="fancy-selector-btn mr-2"
              :class="{
                'fancy-selector-btn--active': selectedTissueNames.length > 0,
                'fancy-selector-btn--open': tissueMenuOpen
              }"
            >
              <!-- Search mode: menu is open -->
              <template v-if="tissueMenuOpen">
                <v-icon size="14" class="fancy-btn-icon-search">mdi-magnify</v-icon>
                <input
                  ref="tissueInputRef"
                  v-model="tissueSearch"
                  class="fancy-btn-search-input"
                  placeholder="Search tissues..."
                  @click.stop
                  @keydown.escape="tissueMenuOpen = false"
                />
              </template>
              <!-- Default mode -->
              <template v-else>
                <span class="fancy-btn-icon">
                  <v-icon size="15">mdi-map-marker-path</v-icon>
                </span>
                <span class="fancy-btn-label">Tissue</span>
                <span
                  v-if="tissueList.length > 0"
                  class="fancy-btn-badge"
                  :class="{ 'fancy-btn-badge--active': selectedTissueNames.length > 0 }"
                >{{ selectedTissueNames.length }}/{{ tissueList.length }}</span>
                <v-icon size="13" class="fancy-btn-chevron">mdi-chevron-down</v-icon>
              </template>
            </div>
          </template>
          <v-card class="selector-dropdown-card">
            <v-card-text class="pa-1">
              <div v-if="filteredTissueList.length === 0" class="text-caption text-grey pa-2">No tissues found</div>
              <v-list density="compact" class="selector-list">
                <v-list-item
                  v-for="sample in filteredTissueList"
                  :key="sample.name"
                  class="selector-list-item"
                  @click="toggleSample(sample.name)"
                >
                  <template #prepend>
                    <v-checkbox-btn
                      :model-value="selectedSampleNames.includes(sample.name)"
                      density="compact"
                      color="primary"
                      @click.stop="toggleSample(sample.name)"
                    />
                  </template>
                  <v-list-item-title class="text-body-2">{{ formatSampleName(sample.name) }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-menu>

        <!-- Cell culture selector -->
        <v-menu
          v-model="cellMenuOpen"
          :close-on-content-click="false"
          max-height="360"
          :width="cellMenuWidth"
          @update:model-value="onCellMenuToggle"
        >
          <template #activator="{ props: menuProps }">
            <div
              v-bind="menuProps"
              ref="cellBtnRef"
              class="fancy-selector-btn"
              :class="{
                'fancy-selector-btn--active': selectedCellNames.length > 0,
                'fancy-selector-btn--open': cellMenuOpen
              }"
            >
              <!-- Search mode: menu is open -->
              <template v-if="cellMenuOpen">
                <v-icon size="14" class="fancy-btn-icon-search">mdi-magnify</v-icon>
                <input
                  ref="cellInputRef"
                  v-model="cellSearch"
                  class="fancy-btn-search-input"
                  placeholder="Search cell cultures..."
                  @click.stop
                  @keydown.escape="cellMenuOpen = false"
                />
              </template>
              <!-- Default mode -->
              <template v-else>
                <span class="fancy-btn-icon">
                  <v-icon size="15">mdi-flask</v-icon>
                </span>
                <span class="fancy-btn-label">Cell Culture</span>
                <span
                  v-if="cellCultureList.length > 0"
                  class="fancy-btn-badge"
                  :class="{ 'fancy-btn-badge--active': selectedCellNames.length > 0 }"
                >{{ selectedCellNames.length }}/{{ cellCultureList.length }}</span>
                <v-icon size="13" class="fancy-btn-chevron">mdi-chevron-down</v-icon>
              </template>
            </div>
          </template>
          <v-card class="selector-dropdown-card">
            <v-card-text class="pa-1">
              <div v-if="filteredCellList.length === 0" class="text-caption text-grey pa-2">No cell cultures found</div>
              <v-list density="compact" class="selector-list">
                <v-list-item
                  v-for="sample in filteredCellList"
                  :key="sample.name"
                  class="selector-list-item"
                  @click="toggleSample(sample.name)"
                >
                  <template #prepend>
                    <v-checkbox-btn
                      :model-value="selectedSampleNames.includes(sample.name)"
                      density="compact"
                      color="primary"
                      @click.stop="toggleSample(sample.name)"
                    />
                  </template>
                  <v-list-item-title class="text-body-2">{{ formatSampleName(sample.name) }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-menu>
      </div>
    </div>

    <!-- SVG Browser -->
    <div ref="browserContainer" class="browser-svg-container">
      <svg
        ref="svgElement"
        :width="containerWidth"
        :height="totalHeight"
        class="genome-svg"
      >
        <defs>
          <!-- Arrow markers for strand direction -->
          <marker
            id="strand-arrow-forward"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="5"
            orient="auto"
          >
            <path d="M0,0 L0,10 L10,5 z" fill="#666" />
          </marker>
          <marker
            id="strand-arrow-reverse"
            markerWidth="10"
            markerHeight="10"
            refX="1"
            refY="5"
            orient="auto"
          >
            <path d="M10,0 L10,10 L0,5 z" fill="#666" />
          </marker>
          
          <!-- Clip path for track content area -->
          <clipPath id="track-clip">
            <rect
              :x="margin.left"
              :y="0"
              :width="containerWidth - margin.left - margin.right"
              :height="totalHeight"
            />
          </clipPath>
        </defs>

        <!-- Main zoomable group -->
        <g ref="zoomGroup">
          <!-- Track labels (fixed left column) -->
          <g ref="labelsGroup" class="track-labels">
            <!-- Rendered by D3 -->
          </g>

          <!-- Coordinate ruler -->
          <g ref="rulerGroup" class="ruler-track" clip-path="url(#track-clip)">
            <!-- Rendered by D3 -->
          </g>

          <!-- Transcript structure track -->
          <g ref="transcriptGroup" class="transcript-track" clip-path="url(#track-clip)">
            <!-- Rendered by D3 -->
          </g>

          <!-- Sample tracks -->
          <g
            v-for="(sample, idx) in activeSamples"
            :key="sample"
            :ref="el => { if (el) sampleGroupRefs[idx] = el }"
            class="sample-track"
            clip-path="url(#track-clip)"
          >
            <!-- Rendered by D3 -->
          </g>
        </g>
      </svg>
    </div>

    <!-- Tooltip is rendered via DOM directly to body (see script) -->
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import { formatSampleName } from '@/utils/formatters'

const props = defineProps({
  transcriptId: { type: String, required: true },
  geneName: { type: String, required: true },
  chromosome: { type: String, required: true },
  strand: { type: String, required: true },
  exons: { type: Array, required: true },  // [{ start, end }]
  cds: { type: Array, default: () => [] },
  apaSites: { type: Array, required: true },  // From locus API
  allSamplesInfo: { type: Array, required: true },  // [{ name, sample_type }]
  trackHeight: { type: Number, default: 40 }
})

// ── Sample selection state ─────────────────────────────────────────────────────

const normalizeSampleType = (sampleType) => {
  const value = String(sampleType ?? '').trim().toLowerCase().replace(/[\s-]+/g, '_')
  if (value === 'tissue' || value.includes('tissue')) return 'tissue'
  return 'cell_culture'
}

const normalizeSampleInfo = (sample) => {
  if (typeof sample === 'string') return { name: sample, sample_type: 'cell_culture' }
  return {
    ...sample,
    sample_type: normalizeSampleType(sample?.sample_type)
  }
}

const sampleDisplayKey = (name) => formatSampleName(name).toLowerCase()

const dedupeSamples = (samples) => {
  const seen = new Set()
  return samples.filter(sample => {
    const key = sampleDisplayKey(sample.name)
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

// Normalise allSamplesInfo: API may return plain strings or {name, sample_type} objects
const normalisedSamplesInfo = computed(() =>
  dedupeSamples((props.allSamplesInfo || []).map(normalizeSampleInfo).filter(s => s.name))
)

// Derived lists by type
const tissueList = computed(() =>
  normalisedSamplesInfo.value
    .filter(s => normalizeSampleType(s.sample_type) === 'tissue')
    .sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''))
)
const cellCultureList = computed(() =>
  normalisedSamplesInfo.value
    .filter(s => normalizeSampleType(s.sample_type) !== 'tissue')
    .sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''))
)

// Selected sample names (string array — what the browser renders)
const selectedSampleNames = ref([])

// Initialize / reset when allSamplesInfo changes
watch(() => props.allSamplesInfo, (newVal) => {
  if (!newVal?.length) {
    selectedSampleNames.value = []
    return
  }
  const normalised = dedupeSamples(newVal.map(normalizeSampleInfo).filter(s => s.name))
  const tissue = normalised.filter(s => normalizeSampleType(s.sample_type) === 'tissue').map(s => s.name).sort()
  const cell = normalised.filter(s => normalizeSampleType(s.sample_type) !== 'tissue').map(s => s.name).sort()
  // Show tissue tracks only if any exist; otherwise show cell culture tracks only.
  // Never mix types on initial load — up to 5 of whichever group is present.
  const defaultGroup = tissue.length > 0 ? tissue : cell
  selectedSampleNames.value = defaultGroup.slice(0, 5)
}, { immediate: true })

// Computed active samples — used everywhere instead of props.samples
const activeSamples = computed(() => selectedSampleNames.value)

// Helper computed: which tissue/cell names are currently selected
const selectedTissueNames = computed(() =>
  selectedSampleNames.value.filter(n => tissueList.value.some(s => s.name === n))
)
const selectedCellNames = computed(() =>
  selectedSampleNames.value.filter(n => cellCultureList.value.some(s => s.name === n))
)

// Menu open/close state
const tissueMenuOpen = ref(false)
const cellMenuOpen = ref(false)

// Button DOM refs (for measuring width to size dropdown)
const tissueBtnRef = ref(null)
const cellBtnRef = ref(null)
const tissueInputRef = ref(null)
const cellInputRef = ref(null)
const tissueMenuWidth = ref('auto')
const cellMenuWidth = ref('auto')

// When menu opens: snapshot button width and autofocus the inline input
const onTissueMenuToggle = async (open) => {
  if (open) {
    if (tissueBtnRef.value) {
      tissueMenuWidth.value = tissueBtnRef.value.offsetWidth + 'px'
    }
    await nextTick()
    tissueInputRef.value?.focus()
  } else {
    tissueSearch.value = ''
  }
}
const onCellMenuToggle = async (open) => {
  if (open) {
    if (cellBtnRef.value) {
      cellMenuWidth.value = cellBtnRef.value.offsetWidth + 'px'
    }
    await nextTick()
    cellInputRef.value?.focus()
  } else {
    cellSearch.value = ''
  }
}

// Fuzzy search state
const tissueSearch = ref('')
const cellSearch = ref('')

// Fuzzy filter helpers
const fuzzyFilter = (list, query) => {
  if (!query) return list
  const q = query.toLowerCase()
  return list.filter(s =>
    s.name.toLowerCase().includes(q) ||
    formatSampleName(s.name).toLowerCase().includes(q)
  )
}
const filteredTissueList = computed(() => fuzzyFilter(tissueList.value, tissueSearch.value))
const filteredCellList = computed(() => fuzzyFilter(cellCultureList.value, cellSearch.value))

// Toggle a sample on/off
const toggleSample = (name) => {
  const idx = selectedSampleNames.value.indexOf(name)
  if (idx === -1) {
    selectedSampleNames.value = [...selectedSampleNames.value, name]
  } else {
    selectedSampleNames.value = selectedSampleNames.value.filter(n => n !== name)
  }
}

// Measure text width using an offscreen canvas
const measureTextWidth = (text, fontSize = 13, fontWeight = '600') => {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  ctx.font = `${fontWeight} ${fontSize}px IBM Plex Sans, sans-serif`
  return ctx.measureText(text).width
}

// Compute dynamic left margin based on all label texts
const dynamicMarginLeft = computed(() => {
  const labels = [
    'Chromosome',   // header line (wider of the two)
    props.transcriptId,
    ...activeSamples.value
  ]
  const maxW = Math.max(...labels.map(l => measureTextWidth(l)))
  // 16px left padding + maxW + 20px right padding before separator
  return Math.ceil(maxW) + 36
})

// Layout — margin.left is reactive
const margin = reactive({ top: 40, right: 16, bottom: 15, left: 150 })
const rulerHeight = 40
const trackPadding = 10
const SAMPLE_TRACK_H = 28
const CDS_COLOR = '#0D7377'
const UTR_COLOR = '#14919B'
const INTRON_COLOR = '#B0B8C1'
const TERMINAL_EXTENSION_COLOR = '#5C8797'

// labelWidth is the usable label area (margin.left minus separator gap)
const labelWidth = computed(() => margin.left - 12)

// Dynamic width: fill container
const containerWidth = ref(1100)

// Computed layout
const trackOffsets = computed(() => {
  const offsets = {
    ruler: margin.top,
    transcript: margin.top + rulerHeight + trackPadding,
    samples: []
  }
  
  const transcriptBottom = offsets.transcript + props.trackHeight
  activeSamples.value.forEach((_, idx) => {
    offsets.samples.push(transcriptBottom + trackPadding + (idx * (SAMPLE_TRACK_H + trackPadding)))
  })
  
  return offsets
})

const totalHeight = computed(() => {
  if (trackOffsets.value.samples.length === 0) {
    return trackOffsets.value.transcript + props.trackHeight + margin.bottom + 20
  }
  const lastSampleOffset = trackOffsets.value.samples[trackOffsets.value.samples.length - 1]
  return lastSampleOffset + SAMPLE_TRACK_H + margin.bottom + 20
})

// Domain: genomic coordinates
const genomicExtent = computed(() => {
  const allPositions = [
    ...props.exons.map(e => [e.start, e.end]).flat(),
    ...props.apaSites.flatMap(s => {
      const range = siteRange(s)
      return [s.mode_site_position, range.start, range.end]
    })
  ]
  if (allPositions.length === 0) return [0, 1000]
  
  const min = Math.min(...allPositions)
  const max = Math.max(...allPositions)
  const padding = Math.max((max - min) * 0.15, 1000)  // At least 1kb padding
  return [min - padding, max + padding]
})

const siteRange = (site) => {
  const fallback = Number(site?.mode_site_position)
  const start = site?.cluster_start != null ? Number(site.cluster_start) : fallback
  const end = site?.cluster_end != null ? Number(site.cluster_end) : fallback
  return {
    start: Math.min(start, end),
    end: Math.max(start, end),
  }
}

const terminalExtensionFor = (sortedExons, strand) => {
  if (!sortedExons.length) return null

  const terminalExon = strand === '-' ? sortedExons[0] : sortedExons[sortedExons.length - 1]
  const ranges = (props.apaSites ?? []).map(siteRange).filter(r =>
    Number.isFinite(r.start) && Number.isFinite(r.end)
  )
  if (!ranges.length) return null

  if (strand === '-') {
    const distalStart = Math.min(...ranges.map(r => r.start))
    if (distalStart >= terminalExon.start) return null
    return {
      start: distalStart,
      end: terminalExon.start,
      anchor: terminalExon.start,
      distal: distalStart,
      direction: 'upstream',
    }
  }

  const distalEnd = Math.max(...ranges.map(r => r.end))
  if (distalEnd <= terminalExon.end) return null
  return {
    start: terminalExon.end,
    end: distalEnd,
    anchor: terminalExon.end,
    distal: distalEnd,
    direction: 'downstream',
  }
}

// D3 scale and zoom
const xScale = ref(null)
const zoomBehavior = ref(null)
const currentTransform = ref(d3.zoomIdentity)
const isTouchLayout = ref(false)

// Refs
const svgElement = ref(null)
const zoomGroup = ref(null)
const labelsGroup = ref(null)
const rulerGroup = ref(null)
const transcriptGroup = ref(null)
// Plain mutable array — NOT a ref. Vue's template ref callbacks do index-based
// assignment (sampleGroupRefs[idx] = el) which breaks on reactive arrays.
let sampleGroupRefs = []
const browserContainer = ref(null)

// Tooltip — single DOM node appended to body, positioned with fixed
let tooltipEl = null

const ensureTooltipEl = () => {
  if (!tooltipEl) {
    tooltipEl = document.createElement('div')
    tooltipEl.className = 'genome-tooltip-global'
    tooltipEl.style.cssText = `
      position: fixed;
      display: none;
      pointer-events: none;
      z-index: 99999;
    `
    document.body.appendChild(tooltipEl)
  }
  return tooltipEl
}

// Tooltip helpers
const showTooltip = (event, title, items) => {
  const el = ensureTooltipEl()

  const rows = items.map(i =>
    `<div style="display:flex;justify-content:space-between;gap:14px;margin-top:4px;line-height:1.5">
      <span style="color:#adb5bd;font-weight:500">${i.label}:</span>
      <span style="font-weight:600;text-align:right;color:#f8f9fa">${i.value}</span>
    </div>`
  ).join('')

  el.innerHTML = `
    <div style="font-weight:700;font-size:14.5px;margin-bottom:6px;padding-bottom:5px;border-bottom:1px solid rgba(255,255,255,0.25)">${title}</div>
    ${rows}
  `

  el.style.padding = '10px 13px'
  el.style.borderRadius = '8px'
  el.style.background = 'rgba(33,37,41,0.95)'
  el.style.border = '1px solid rgba(255,255,255,0.12)'
  el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.35)'
  el.style.backdropFilter = 'blur(8px)'
  el.style.webkitBackdropFilter = 'blur(8px)'
  el.style.minWidth = '190px'
  el.style.maxWidth = '280px'
  el.style.fontSize = '13.5px'
  el.style.fontFamily = 'IBM Plex Sans, sans-serif'
  el.style.color = '#fff'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const OFFSET_X = 14, OFFSET_Y = -10
  const W = el.offsetWidth || 220
  const H = el.offsetHeight || 120
  const vw = window.innerWidth
  const vh = window.innerHeight

  let x = nativeEvent.clientX + OFFSET_X
  let y = nativeEvent.clientY + OFFSET_Y
  if (x + W > vw - 8) x = nativeEvent.clientX - W - OFFSET_X
  if (y + H > vh - 8) y = nativeEvent.clientY - H - Math.abs(OFFSET_Y)
  if (y < 4) y = 4
  if (x < 4) x = 4

  el.style.left = x + 'px'
  el.style.top  = y + 'px'
}

const hideTooltip = () => {
  if (tooltipEl) tooltipEl.style.display = 'none'
}

const showPaSiteTooltip = (event, site, sampleName, sampleData) => {
  const el = ensureTooltipEl()

  const pct = (sampleData.site_abundance * 100).toFixed(1)
  const supportingReads = Number.isSafeInteger(sampleData.site_count) && sampleData.site_count >= 0
    ? sampleData.site_count.toLocaleString()
    : 'N/A'
  const pasTypeColors = {
    canonical: { label: 'Canonical', bg: 'rgba(13,115,119,0.12)', border: 'rgba(13,115,119,0.35)', text: '#0A5C5F' },
    variant: { label: 'Variant', bg: 'rgba(53,92,125,0.14)', border: 'rgba(79,127,164,0.42)', text: '#275A7B' },
    upstream: { label: 'Upstream', bg: 'rgba(169,111,76,0.14)', border: 'rgba(169,111,76,0.42)', text: '#7A472B' },
    downstream: { label: 'Downstream', bg: 'rgba(116,106,158,0.14)', border: 'rgba(127,115,179,0.42)', text: '#574C88' },
    plant_nue: { label: 'Plant NUE', bg: 'rgba(32,130,111,0.14)', border: 'rgba(58,146,127,0.42)', text: '#176353' },
    plant_fue: { label: 'Plant FUE', bg: 'rgba(125,142,76,0.14)', border: 'rgba(132,147,79,0.42)', text: '#59652E' },
    yeast_ee_pe: { label: 'Yeast EE + PE', bg: 'rgba(45,118,140,0.14)', border: 'rgba(74,130,151,0.42)', text: '#285C70' },
    yeast_positioning: { label: 'Yeast PE', bg: 'rgba(185,139,57,0.14)', border: 'rgba(181,138,63,0.42)', text: '#75591F' },
    yeast_efficiency: { label: 'Yeast EE', bg: 'rgba(169,111,76,0.14)', border: 'rgba(169,111,76,0.42)', text: '#75492F' },
    yeast_u_rich: { label: 'Yeast U-rich', bg: 'rgba(91,126,108,0.14)', border: 'rgba(102,133,116,0.42)', text: '#3F5F4E' },
    pombe_a_rich: { label: 'S. pombe A-rich', bg: 'rgba(35,125,121,0.14)', border: 'rgba(61,139,135,0.42)', text: '#1B615E' },
    pombe_gua_uag: { label: 'S. pombe GUA/UAG', bg: 'rgba(104,103,151,0.14)', border: 'rgba(119,117,165,0.42)', text: '#52517C' },
    pombe_uag: { label: 'S. pombe UAG', bg: 'rgba(122,105,153,0.14)', border: 'rgba(134,116,165,0.42)', text: '#5B4D77' },
    pombe_gua: { label: 'S. pombe GUA', bg: 'rgba(80,117,151,0.14)', border: 'rgba(100,131,160,0.42)', text: '#405F79' },
    pombe_u_rich: { label: 'S. pombe U-rich', bg: 'rgba(105,128,106,0.14)', border: 'rgba(117,140,118,0.42)', text: '#4C654D' },
    not_assessed: { label: 'Not assessed', bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.30)', text: '#475569' },
  }
  const pasColor = pasTypeColors[site.pas_type] || { bg: 'rgba(100,116,139,0.10)', border: 'rgba(100,116,139,0.30)', text: '#475569' }
  const pasLabel = pasColor.label || (site.pas_type
    ? site.pas_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : 'N/A')

  el.innerHTML = `
    <div style="padding:13px 15px">

      <div style="font-size:10.5px;letter-spacing:0.10em;color:#0D7377;font-weight:700;text-transform:uppercase;margin-bottom:3px">PA Site</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:11.5px;color:#0f172a;word-break:break-all;line-height:1.5;font-weight:600;margin-bottom:10px">${site.unified_id}</div>

      <div style="height:1px;background:rgba(13,115,119,0.15);margin-bottom:9px"></div>

      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">

        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Rep. Position</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${site.mode_site_position.toLocaleString()}</span>

        <span style="color:#475569;font-size:12.5px">Sample</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:600;font-family:'IBM Plex Sans',sans-serif">${formatSampleName(sampleName)}</span>

        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Supporting reads</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${supportingReads}</span>

        <span style="color:#475569;font-size:12.5px">Abundance</span>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:60px;height:5px;background:rgba(13,115,119,0.15);border-radius:3px;overflow:hidden">
            <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#0D7377,#14919B);border-radius:3px"></div>
          </div>
          <span style="color:#0D7377;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${pct}%</span>
        </div>

      </div>

      <div style="height:1px;background:rgba(13,115,119,0.15);margin:9px 0"></div>

      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">

        <span style="color:#475569;font-size:12.5px">PAS Motif</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif;letter-spacing:0.04em">${site.pas_motif || 'N/A'}</span>

        <span style="color:#475569;font-size:12.5px">PAS Offset</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:600;font-family:'IBM Plex Sans',sans-serif">${site.pas_position != null ? site.pas_position + '\u202fbp' : 'N/A'}</span>

        <span style="color:#475569;font-size:12.5px">PAS Type</span>
        <span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:600;background:${pasColor.bg};border:1px solid ${pasColor.border};color:${pasColor.text};letter-spacing:0.03em;justify-self:start;white-space:nowrap">${pasLabel}</span>

      </div>
    </div>
  `

  el.style.padding = '0'
  el.style.borderRadius = '12px'
  el.style.background = 'rgba(255,255,255,0.78)'
  el.style.backdropFilter = 'blur(24px) saturate(180%)'
  el.style.webkitBackdropFilter = 'blur(24px) saturate(180%)'
  el.style.border = '1px solid rgba(13,115,119,0.20)'
  el.style.boxShadow = '0 8px 32px rgba(13,115,119,0.12), 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9)'
  el.style.minWidth = '240px'
  el.style.maxWidth = '310px'
  el.style.fontSize = '13px'
  el.style.fontFamily = 'IBM Plex Sans, sans-serif'
  el.style.color = '#0f172a'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const W = el.offsetWidth || 260
  const H = el.offsetHeight || 200
  const vw = window.innerWidth
  const vh = window.innerHeight
  const OFFSET_X = 14, OFFSET_Y = -10

  let x = nativeEvent.clientX + OFFSET_X
  let y = nativeEvent.clientY + OFFSET_Y
  if (x + W > vw - 8) x = nativeEvent.clientX - W - OFFSET_X
  if (y + H > vh - 8) y = nativeEvent.clientY - H - Math.abs(OFFSET_Y)
  if (y < 4) y = 4
  if (x < 4) x = 4

  el.style.left = x + 'px'
  el.style.top  = y + 'px'
}

const showExonTooltip = (event, displayNum, exon) => {
  const el = ensureTooltipEl()

  el.innerHTML = `
    <div style="padding:13px 15px">
      <div style="font-size:10.5px;letter-spacing:0.10em;color:#0D7377;font-weight:700;text-transform:uppercase;margin-bottom:3px">Exon</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:14px;color:#0f172a;font-weight:700;margin-bottom:10px">Exon ${displayNum}</div>
      <div style="height:1px;background:rgba(13,115,119,0.15);margin-bottom:9px"></div>
      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Position</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${exon.start.toLocaleString()} – ${exon.end.toLocaleString()}</span>
        <span style="color:#475569;font-size:12.5px">Length</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${(exon.end - exon.start + 1).toLocaleString()} bp</span>
      </div>
    </div>
  `

  el.style.padding = '0'
  el.style.borderRadius = '12px'
  el.style.background = 'rgba(255,255,255,0.78)'
  el.style.backdropFilter = 'blur(24px) saturate(180%)'
  el.style.webkitBackdropFilter = 'blur(24px) saturate(180%)'
  el.style.border = '1px solid rgba(13,115,119,0.20)'
  el.style.boxShadow = '0 8px 32px rgba(13,115,119,0.12), 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9)'
  el.style.minWidth = '200px'
  el.style.maxWidth = '280px'
  el.style.fontSize = '13px'
  el.style.fontFamily = 'IBM Plex Sans, sans-serif'
  el.style.color = '#0f172a'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const W = el.offsetWidth || 220
  const H = el.offsetHeight || 120
  const vw = window.innerWidth
  const vh = window.innerHeight
  const OFFSET_X = 14, OFFSET_Y = -10

  let x = nativeEvent.clientX + OFFSET_X
  let y = nativeEvent.clientY + OFFSET_Y
  if (x + W > vw - 8) x = nativeEvent.clientX - W - OFFSET_X
  if (y + H > vh - 8) y = nativeEvent.clientY - H - Math.abs(OFFSET_Y)
  if (y < 4) y = 4
  if (x < 4) x = 4

  el.style.left = x + 'px'
  el.style.top  = y + 'px'
}

const showTerminalExtensionTooltip = (event, extension) => {
  const el = ensureTooltipEl()
  const length = Math.abs(extension.end - extension.start)

  el.innerHTML = `
    <div style="padding:13px 15px">
      <div style="font-size:10.5px;letter-spacing:0.10em;color:#B7791F;font-weight:700;text-transform:uppercase;margin-bottom:3px">APA-supported extension</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:14px;color:#0f172a;font-weight:700;margin-bottom:10px">Terminal exon extension</div>
      <div style="height:1px;background:rgba(183,121,31,0.20);margin-bottom:9px"></div>
      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Transcript</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:600;font-family:'IBM Plex Sans',sans-serif">${props.transcriptId}</span>
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Extension</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${extension.start.toLocaleString()} – ${extension.end.toLocaleString()}</span>
        <span style="color:#475569;font-size:12.5px">Length</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${length.toLocaleString()} bp</span>
      </div>
      <div style="margin-top:10px;color:#64748b;font-size:12px;line-height:1.45">
        PA sites extend beyond the annotated terminal exon, suggesting an incomplete transcript end in the reference annotation.
      </div>
    </div>
  `

  el.style.padding = '0'
  el.style.borderRadius = '12px'
  el.style.background = 'rgba(255,255,255,0.84)'
  el.style.backdropFilter = 'blur(24px) saturate(180%)'
  el.style.webkitBackdropFilter = 'blur(24px) saturate(180%)'
  el.style.border = '1px solid rgba(183,121,31,0.25)'
  el.style.boxShadow = '0 8px 32px rgba(183,121,31,0.13), 0 2px 8px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9)'
  el.style.minWidth = '260px'
  el.style.maxWidth = '340px'
  el.style.fontSize = '13px'
  el.style.fontFamily = 'IBM Plex Sans, sans-serif'
  el.style.color = '#0f172a'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const W = el.offsetWidth || 290
  const H = el.offsetHeight || 170
  const vw = window.innerWidth
  const vh = window.innerHeight
  const OFFSET_X = 14, OFFSET_Y = -10

  let x = nativeEvent.clientX + OFFSET_X
  let y = nativeEvent.clientY + OFFSET_Y
  if (x + W > vw - 8) x = nativeEvent.clientX - W - OFFSET_X
  if (y + H > vh - 8) y = nativeEvent.clientY - H - Math.abs(OFFSET_Y)
  if (y < 4) y = 4
  if (x < 4) x = 4

  el.style.left = x + 'px'
  el.style.top  = y + 'px'
}

// Initialize scale
const initScale = () => {
  // Base scale maps the content region (exons + APA sites + 5% pad) directly to the
  // track pixel range. This means k=1 always equals "full-content fit", which makes
  // scaleExtent([1, 100]) and translateExtent behave correctly without any fitK gymnastics.
  const allPositions = [
    ...props.exons.map(e => [e.start, e.end]).flat(),
    ...props.apaSites.flatMap(s => {
      const range = siteRange(s)
      return [s.mode_site_position, range.start, range.end]
    })
  ]
  const cMin = allPositions.length ? Math.min(...allPositions) : 0
  const cMax = allPositions.length ? Math.max(...allPositions) : 1000
  const span = cMax - cMin
  const pad = span * 0.05
  xScale.value = d3.scaleLinear()
    .domain([cMin - pad, cMax + pad])
    .range([margin.left, containerWidth.value - margin.right])
}

// IGV-style coordinate formatting — unit chosen by visible range, not value magnitude
const formatCoordinate = (value) => {
  const domain = xScale.value ? xScale.value.domain() : genomicExtent.value
  const range = domain[1] - domain[0]

  if (range >= 1_000_000) {
    // Mb — 1 decimal is enough when range spans multiple Mb
    return (value / 1_000_000).toFixed(1) + ' Mb'
  } else if (range >= 10_000) {
    // Kb — show 1 decimal; tighten to 2 decimals when range < 100 Kb for precision
    const dec = range < 100_000 ? 2 : 1
    return (value / 1_000).toFixed(dec) + ' Kb'
  } else if (range >= 1_000) {
    // Kb with 3 decimals (range is a few Kb — need sub-Kb distinction)
    return (value / 1_000).toFixed(3) + ' Kb'
  } else {
    // bp — plain integer with locale separator
    return Math.round(value).toLocaleString() + ' bp'
  }
}

// Render coordinate ruler with smart label placement
const renderRuler = () => {
  const g = d3.select(rulerGroup.value)
  g.selectAll('*').remove()

  g.attr('transform', `translate(0, ${trackOffsets.value.ruler})`)

  // Background
  g.append('rect')
    .attr('x', margin.left)
    .attr('y', 0)
    .attr('width', containerWidth.value - margin.left - margin.right)
    .attr('height', rulerHeight)
    .attr('fill', '#FAFBFC')
    .attr('stroke', 'rgba(0, 0, 0, 0.12)')
    .attr('stroke-width', 1)

  // ── Tick value generation ────────────────────────────────────────────────────
  // Estimate the pixel width of a formatted label (IBM Plex Sans 12px ~6.5px per char)
  const domain = xScale.value.domain()
  const visibleRange = domain[1] - domain[0]
  const trackWidth = containerWidth.value - margin.left - margin.right

  // Sample label width using a representative value near the centre of the domain
  const sampleLabel = formatCoordinate((domain[0] + domain[1]) / 2)
  const labelPx = sampleLabel.length * 9    // ~9px per char for IBM Plex Sans 500 12px
  const minSpacingPx = labelPx + 40         // label width + 40px breathing room

  // How many ticks fit?
  const maxTicks = Math.max(2, Math.floor(trackWidth / minSpacingPx))

  // Pick a "nice" genomic step that is a round number (1/2/5 × 10^n)
  const rawStep = visibleRange / maxTicks
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const factor = rawStep / magnitude
  const niceStep = factor < 1.5 ? magnitude
    : factor < 3.5 ? 2 * magnitude
    : factor < 7.5 ? 5 * magnitude
    : 10 * magnitude

  // Generate tick values aligned to niceStep multiples
  const start = Math.ceil(domain[0] / niceStep) * niceStep
  const tickValues = []
  for (let v = start; v <= domain[1]; v += niceStep) {
    tickValues.push(v)
  }

  const axis = d3.axisTop(xScale.value)
    .tickValues(tickValues)
    .tickFormat(formatCoordinate)
    .tickSize(8)

  const axisGroup = g.append('g')
    .attr('transform', `translate(0, ${rulerHeight - 5})`)
    .call(axis)

  // Style axis
  axisGroup.selectAll('.domain')
    .attr('stroke', 'rgba(0, 0, 0, 0.2)')
    .attr('stroke-width', 1)

  axisGroup.selectAll('line')
    .attr('stroke', '#999')

  axisGroup.selectAll('text')
    .style('font-family', 'IBM Plex Sans, sans-serif')
    .style('font-size', '12px')
    .style('font-weight', '500')
    .style('fill', 'rgba(0, 0, 0, 0.6)')
    .attr('dy', '-5px')

  // Chromosome label is rendered in renderLabels() (left margin)
}

// Render track labels (fixed left margin)
const renderLabels = () => {
  const g = d3.select(labelsGroup.value)
  g.selectAll('*').remove()

  // Chromosome label (in left margin, aligned with ruler) — two lines, centered
  const chrText = g.append('text')
    .attr('x', labelWidth.value / 2)
    .attr('y', trackOffsets.value.ruler + rulerHeight / 2 - 7)
    .attr('text-anchor', 'middle')
    .style('font-family', 'IBM Plex Sans, sans-serif')

  chrText.append('tspan')
    .attr('x', labelWidth.value / 2)
    .attr('dy', '0')
    .style('font-size', '12.5px')
    .style('font-weight', '600')
    .style('fill', '#475569')
    .text('Chromosome')

  chrText.append('tspan')
    .attr('x', labelWidth.value / 2)
    .attr('dy', '16')
    .style('font-size', '14.5px')
    .style('font-weight', '700')
    .style('fill', '#0D7377')
    .text(props.chromosome)

  // Transcript label
  g.append('text')
    .attr('x', labelWidth.value / 2)
    .attr('y', trackOffsets.value.transcript + props.trackHeight / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'middle')
    .style('font-family', 'IBM Plex Sans, sans-serif')
    .style('font-size', '14.5px')
    .style('font-weight', '600')
    .style('fill', '#0D7377')
    .text(`${props.transcriptId}`)

  // Sample labels
  activeSamples.value.forEach((sample, idx) => {
    g.append('rect')
      .attr('x', 8)
      .attr('y', trackOffsets.value.samples[idx] + SAMPLE_TRACK_H / 2 - 12)
      .attr('width', labelWidth.value - 16)
      .attr('height', 24)
      .attr('fill', idx % 2 === 0 ? 'rgba(13, 115, 119, 0.06)' : 'rgba(13, 115, 119, 0.1)')
      .attr('rx', 4)

    g.append('text')
      .attr('x', labelWidth.value / 2)
      .attr('y', trackOffsets.value.samples[idx] + SAMPLE_TRACK_H / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .style('font-family', 'IBM Plex Sans, sans-serif')
      .style('font-size', '12px')
      .style('font-weight', '500')
      .style('fill', '#475569')
      .text(formatSampleName(sample))
  })

  // Vertical separator line
  g.append('line')
    .attr('x1', margin.left - 5)
    .attr('x2', margin.left - 5)
    .attr('y1', trackOffsets.value.ruler)
    .attr('y2', totalHeight.value - margin.bottom)
    .attr('stroke', 'rgba(0, 0, 0, 0.12)')
    .attr('stroke-width', 1)
}

// Render transcript structure with CLEAR formatting
const renderTranscript = () => {
  const g = d3.select(transcriptGroup.value)
  g.selectAll('*').remove()

  g.attr('transform', `translate(0, ${trackOffsets.value.transcript})`)

  const trackY = props.trackHeight / 2

  // Track background
  g.append('rect')
    .attr('x', margin.left)
    .attr('y', 0)
    .attr('width', containerWidth.value - margin.left - margin.right)
    .attr('height', props.trackHeight)
    .attr('fill', '#FFFFFF')
    .attr('stroke', 'rgba(0, 0, 0, 0.12)')
    .attr('stroke-width', 1)

  // Intron backbone line (thin gray line connecting exons)
  const sortedExons = [...props.exons].sort((a, b) => a.start - b.start)
  if (sortedExons.length > 1) {
    const backboneStart = xScale.value(sortedExons[0].start)
    const backboneEnd = xScale.value(sortedExons[sortedExons.length - 1].end)
    
    g.append('line')
      .attr('class', 'intron-backbone')
      .attr('x1', backboneStart)
      .attr('x2', backboneEnd)
      .attr('y1', trackY)
      .attr('y2', trackY)
      .attr('stroke', '#B0B8C1')
      .attr('stroke-width', 2)

    // Intron direction chevrons (replaces 3' end arrow)
    for (let i = 0; i < sortedExons.length - 1; i++) {
      const intronStartX = xScale.value(sortedExons[i].end)
      const intronEndX = xScale.value(sortedExons[i + 1].start)
      const intronWidth = intronEndX - intronStartX

      // Only add chevrons if intron region is wide enough
      if (intronWidth > 20) {
        const arrowSpacing = 40
        const numArrows = Math.max(1, Math.floor(intronWidth / arrowSpacing))
        const actualSpacing = intronWidth / (numArrows + 1)
        const chevronSize = 4

        for (let j = 1; j <= numArrows; j++) {
          const ax = intronStartX + j * actualSpacing
          const chevronPath = props.strand === '+'
            ? `M${ax - chevronSize},${trackY - chevronSize} L${ax + chevronSize},${trackY} L${ax - chevronSize},${trackY + chevronSize}`
            : `M${ax + chevronSize},${trackY - chevronSize} L${ax - chevronSize},${trackY} L${ax + chevronSize},${trackY + chevronSize}`

          g.append('path')
            .attr('d', chevronPath)
            .attr('fill', 'none')
            .attr('stroke', '#999')
            .attr('stroke-width', 1.5)
            .attr('stroke-linecap', 'round')
            .attr('stroke-linejoin', 'round')
        }
      }
    }
  }

  // Create CDS lookup set for fast checking
  const cdsSet = new Set(props.cds.map(c => `${c.start}-${c.end}`))
  const terminalExtension = terminalExtensionFor(sortedExons, props.strand)

  if (terminalExtension) {
    const x1 = xScale.value(terminalExtension.start)
    const x2 = xScale.value(terminalExtension.end)
    const x = Math.min(x1, x2)
    const w = Math.max(3, Math.abs(x2 - x1))
    const exonHeight = 20
    const extensionStroke = 1
    const extensionH = exonHeight - extensionStroke * 2

    const ext = g.append('g')
      .attr('class', 'terminal-extension')
      .style('cursor', 'help')

    ext.append('rect')
      .attr('x', x)
      .attr('y', trackY - extensionH / 2)
      .attr('width', w)
      .attr('height', extensionH)
      .attr('fill', TERMINAL_EXTENSION_COLOR)
      .attr('fill-opacity', 0.16)
      .attr('stroke', TERMINAL_EXTENSION_COLOR)
      .attr('stroke-width', extensionStroke)
      .attr('stroke-dasharray', '4,3')
      .attr('rx', 3)

    ext.append('rect')
      .attr('x', x)
      .attr('y', 0)
      .attr('width', w)
      .attr('height', props.trackHeight)
      .attr('fill', 'transparent')

    if (w > 72) {
      ext.append('text')
        .attr('x', x + w / 2)
        .attr('y', trackY)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '10.5px')
        .style('font-weight', '700')
        .style('fill', TERMINAL_EXTENSION_COLOR)
        .style('pointer-events', 'none')
        .text('APA extension')
    }

    ext
      .on('mouseenter', function(event) {
        d3.select(this).select('rect').attr('fill-opacity', 0.24)
        showTerminalExtensionTooltip(event, terminalExtension)
      })
      .on('mousemove', function(event) {
        showTerminalExtensionTooltip(event, terminalExtension)
      })
      .on('mouseleave', function() {
        d3.select(this).select('rect').attr('fill-opacity', 0.16)
        hideTooltip()
      })
  }

  // Render exons with DISTINCT CDS vs UTR styling
  sortedExons.forEach((exon, idx) => {
    const displayNum = props.strand === '-' ? sortedExons.length - idx : idx + 1
    const isCDS = cdsSet.has(`${exon.start}-${exon.end}`)
    const exonHeight = 20
    const exonColor = isCDS ? CDS_COLOR : UTR_COLOR
    
    const x = xScale.value(exon.start)
    const width = Math.max(3, xScale.value(exon.end) - x)

    g.append('rect')
      .attr('class', 'exon-box')
      .attr('x', x)
      .attr('y', trackY - exonHeight / 2)
      .attr('width', width)
      .attr('height', exonHeight)
      .attr('fill', exonColor)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('rx', 3)
      .style('cursor', 'pointer')
      .on('mouseenter', function(event) {
        d3.select(this)
          .attr('opacity', 0.8)
          .attr('stroke', '#000')
        showExonTooltip(event, displayNum, exon)
      })
      .on('mousemove', function(event) {
        showExonTooltip(event, displayNum, exon)
      })
      .on('mouseleave', function() {
        d3.select(this)
          .attr('opacity', 1)
          .attr('stroke', '#fff')
        hideTooltip()
      })

    // Add exon number label (only if wide enough)
    if (width > 30) {
      g.append('text')
        .attr('x', x + width / 2)
        .attr('y', trackY)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('font-weight', '600')
        .style('fill', '#fff')
        .style('pointer-events', 'none')
        .text(displayNum)
    }
  })
}

// Render APA sites for each sample (CLEAR non-overlapping markers)
const renderSampleTracks = () => {
  activeSamples.value.forEach((sample, idx) => {
    const el = sampleGroupRefs[idx]
    if (!el) return  // guard: DOM element not yet ready — skip silently
    const g = d3.select(el)
    g.selectAll('*').remove()

    g.attr('transform', `translate(0, ${trackOffsets.value.samples[idx]})`)

    const trackY = SAMPLE_TRACK_H

    // Track background with zebra striping
    g.append('rect')
      .attr('x', margin.left)
      .attr('y', 0)
      .attr('width', containerWidth.value - margin.left - margin.right)
      .attr('height', SAMPLE_TRACK_H)
      .attr('fill', idx % 2 === 0 ? '#FFFFFF' : '#FAFBFC')
      .attr('stroke', 'rgba(0, 0, 0, 0.12)')
      .attr('stroke-width', 1)

    // APA sites — asymmetric Gaussian peak (split-normal)
    const maxCurveH = trackY - 4
    const MIN_HALF_PX = 8
    const COLOR = '#D45D79'
    const sampleKey = sampleDisplayKey(sample)

    props.apaSites.forEach((site) => {
      const sampleData = site.sample_details?.find(sd => sampleDisplayKey(sd.sample_name) === sampleKey)
      if (!sampleData || sampleData.site_abundance === 0) return

      const abundance = sampleData.site_abundance
      const xRep = xScale.value(site.mode_site_position)

      let xStart, xEnd
      if (site.cluster_start != null && site.cluster_end != null) {
        const gStart = Number(site.cluster_start)
        const gEnd = Number(site.cluster_end)
        xStart = gStart === gEnd ? xRep - MIN_HALF_PX : Math.min(xScale.value(gStart), xRep - MIN_HALF_PX)
        xEnd = gStart === gEnd ? xRep + MIN_HALF_PX : Math.max(xScale.value(gEnd), xRep + MIN_HALF_PX)
      } else {
        // Backward-compatible fallback for legacy IDs formatted as chr:start-end:strand.
        const rangeMatch = site.unified_id.match(/:(\d+)-(\d+):/)
        if (rangeMatch) {
          const gStart = parseInt(rangeMatch[1])
          const gEnd = parseInt(rangeMatch[2])
          xStart = gStart === gEnd ? xRep - MIN_HALF_PX : Math.min(xScale.value(gStart), xRep - MIN_HALF_PX)
          xEnd = gStart === gEnd ? xRep + MIN_HALF_PX : Math.max(xScale.value(gEnd), xRep + MIN_HALF_PX)
        } else {
          xStart = xRep - MIN_HALF_PX
          xEnd = xRep + MIN_HALF_PX
        }
      }

      const sigmaL = (xRep - xStart) / 2.5
      const sigmaR = (xEnd - xRep) / 2.5
      const peakH = Math.max(4, abundance * maxCurveH)

      // Sample 60 points for a smooth split-normal curve
      const N = 60
      const pts = []
      for (let i = 0; i <= N; i++) {
        const px = xStart + (i / N) * (xEnd - xStart)
        const dx = px - xRep
        const sigma = dx <= 0 ? sigmaL : sigmaR
        const y = peakH * Math.exp(-0.5 * (dx / sigma) ** 2)
        pts.push([px, trackY - y])
      }

      const lineGen = d3.line().curve(d3.curveCatmullRom.alpha(0.5))
      const curvePath = lineGen(pts)

      // Closed area path
      const areaPath = `M ${xStart} ${trackY} ` +
        pts.map(([px, py]) => `L ${px} ${py}`).join(' ') +
        ` L ${xEnd} ${trackY} Z`

      const marker = g.append('g').attr('class', 'apa-marker').style('cursor', 'pointer')

      // Filled area under curve
      marker.append('path')
        .attr('d', areaPath)
        .attr('fill', COLOR)
        .attr('fill-opacity', 0.18)
        .attr('stroke', 'none')

      // Curve outline
      marker.append('path')
        .attr('d', curvePath)
        .attr('fill', 'none')
        .attr('stroke', COLOR)
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.85)

      // Dashed vertical at representative position
      marker.append('line')
        .attr('x1', xRep).attr('x2', xRep)
        .attr('y1', trackY - peakH).attr('y2', trackY)
        .attr('stroke', COLOR)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '2,2')
        .attr('stroke-opacity', 0.7)

      // Invisible hit area for hover
      marker.append('rect')
        .attr('x', xStart)
        .attr('y', 0)
        .attr('width', Math.max(12, xEnd - xStart))
        .attr('height', SAMPLE_TRACK_H)
        .attr('fill', 'transparent')

      marker
        .on('mouseenter', function(event) {
          d3.select(this).select('path:nth-child(2)').attr('stroke-width', 2.5).attr('stroke-opacity', 1)
          d3.select(this).select('path:first-child').attr('fill-opacity', 0.32)
          showPaSiteTooltip(event, site, sample, sampleData)
        })
        .on('mousemove', function(event) {
          showPaSiteTooltip(event, site, sample, sampleData)
        })
        .on('mouseleave', function() {
          d3.select(this).select('path:nth-child(2)').attr('stroke-width', 1.5).attr('stroke-opacity', 0.85)
          d3.select(this).select('path:first-child').attr('fill-opacity', 0.18)
          hideTooltip()
        })
    })
  })
}

// Zoom behavior
// Because initScale() maps content (+ 5% pad) directly to the track, k=1 always means
// "full-content fit". scaleExtent([1, 100]) naturally enforces this as the zoom floor.
// translateExtent is set so the content cannot be panned off-screen:
//   at any zoom level the content endpoints are constrained to the track edges.
let _frozenBaseScale = null

const setupZoom = () => {
  if (isTouchLayout.value) {
    zoomBehavior.value = null
    currentTransform.value = d3.zoomIdentity
    d3.select(svgElement.value).on('.zoom', null)
    d3.select(svgElement.value).on('mouseleave.tooltip', hideTooltip)
    return
  }

  const baseScale = xScale.value.copy()  // Snapshot of base (k=1) scale — never mutated
  _frozenBaseScale = baseScale

  const trackLeft = margin.left
  const trackRight = containerWidth.value - margin.right

  // translateExtent: content pixel bounds in base-scale space equal the track edges.
  // D3's constrain function ensures these bounds are respected at all zoom levels,
  // so the user can never pan the transcript completely off-screen.
  zoomBehavior.value = d3.zoom()
    .scaleExtent([1, 100])
    .translateExtent([[trackLeft, -Infinity], [trackRight, Infinity]])
    .extent([[trackLeft, 0], [trackRight, totalHeight.value]])
    .on('zoom', (event) => {
      currentTransform.value = event.transform
      xScale.value = event.transform.rescaleX(baseScale)
      redrawTracks()
    })

  d3.select(svgElement.value).call(zoomBehavior.value)
  d3.select(svgElement.value).on('mouseleave.tooltip', hideTooltip)

  // k=1 identity transform is the fit view — apply immediately (no transition on first load)
  d3.select(svgElement.value).call(zoomBehavior.value.transform, d3.zoomIdentity)
}

// Zoom controls
const zoomIn = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  d3.select(svgElement.value)
    .transition()
    .duration(300)
    .call(zoomBehavior.value.scaleBy, 1.5)
}

const zoomOut = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  d3.select(svgElement.value)
    .transition()
    .duration(300)
    .call(zoomBehavior.value.scaleBy, 0.67)
}

const resetZoom = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  // k=1 identity transform is exactly the fit view (initScale maps content to track at k=1)
  d3.select(svgElement.value)
    .transition()
    .duration(500)
    .call(zoomBehavior.value.transform, d3.zoomIdentity)
}

// Redraw all tracks with the current xScale (no scale reinit — safe to call during zoom)
const redrawTracks = () => {
  renderLabels()
  renderRuler()
  renderTranscript()
  renderSampleTracks()
}

// Full render: reinitialise scale then draw everything. Only call on first mount or resize.
const render = () => {
  initScale()
  redrawTracks()
}

// Measure container width
const resizeObserver = ref(null)

const measureWidth = () => {
  if (browserContainer.value) {
    const previousTouchLayout = isTouchLayout.value
    const rect = browserContainer.value.getBoundingClientRect()
    const visibleWidth = Math.floor(rect.width - 24)
    if (visibleWidth <= 0) return false

    const mobile = window.matchMedia('(max-width: 640px)').matches
    const tablet = window.matchMedia('(max-width: 900px)').matches
    const coarsePointer = window.matchMedia('(pointer: coarse)').matches
    const hoverless = window.matchMedia('(hover: none)').matches
    isTouchLayout.value = tablet && (coarsePointer || hoverless)

    // Account for container padding (12px each side)
    if (mobile) {
      containerWidth.value = Math.max(760, Math.floor(visibleWidth * 2.05))
    } else if (tablet) {
      containerWidth.value = Math.max(980, Math.floor(visibleWidth * 1.45))
    } else {
      containerWidth.value = visibleWidth
    }

    return previousTouchLayout !== isTouchLayout.value
  }
  return false
}

// Initialize on mount
// Wheel handler — stored so we can remove it on unmount
let wheelHandler = null

const syncDesktopWheelHandler = () => {
  if (!browserContainer.value) return
  if (isTouchLayout.value) {
    if (wheelHandler) {
      browserContainer.value.removeEventListener('wheel', wheelHandler)
      wheelHandler = null
    }
    return
  }
  if (!wheelHandler) {
    // Desktop-only: keep wheel input dedicated to D3 zoom while cursor is inside.
    wheelHandler = (e) => e.preventDefault()
    browserContainer.value.addEventListener('wheel', wheelHandler, { passive: false })
  }
}

onMounted(async () => {
  await nextTick()
  measureWidth()
  if (props.exons && props.exons.length > 0) {
    // Clear refs and wait two ticks so the v-for <g> elements exist
    sampleGroupRefs = []
    await nextTick()
    render()
    setupZoom()
  }
  // Watch for container resize
  resizeObserver.value = new ResizeObserver(async () => {
    const interactionModeChanged = measureWidth()
    if (props.exons && props.exons.length > 0) {
      render()
      if (interactionModeChanged) {
        setupZoom()
        syncDesktopWheelHandler()
      }
    }
  })
  if (browserContainer.value) {
    resizeObserver.value.observe(browserContainer.value)
    syncDesktopWheelHandler()
  }
})

onBeforeUnmount(() => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
  if (browserContainer.value && wheelHandler) {
    browserContainer.value.removeEventListener('wheel', wheelHandler)
    wheelHandler = null
  }
  if (tooltipEl) {
    tooltipEl.remove()
    tooltipEl = null
  }
})

// Re-render on data changes (including active sample selection changes)
watch(() => [props.exons, props.apaSites, activeSamples.value], async () => {
  // Clear stale refs so Vue can repopulate them from scratch
  sampleGroupRefs = []
  // First tick: Vue removes/unmounts old <g> elements from v-for
  await nextTick()
  // Second tick: Vue creates new <g> elements for updated activeSamples
  await nextTick()
  if (props.exons && props.exons.length > 0) {
    if (zoomBehavior.value && !isTouchLayout.value) {
      // Zoom already active — only redraw, don't reinit scale (would reset zoom)
      redrawTracks()
    } else {
      render()
      setupZoom()
    }
  }
}, { deep: true })

// Sync margin.left whenever dynamic label width changes, then full re-render + zoom reset
// (layout has changed — must reinit scale range and zoom base)
watch(dynamicMarginLeft, (newLeft) => {
  margin.left = newLeft
  nextTick(() => {
    if (props.exons && props.exons.length > 0) {
      render()
      setupZoom()
    }
  })
}, { immediate: true })
</script>

<style scoped>
.apa-genome-browser {
  width: 100%;
  background: transparent;
  border-radius: 8px;
  padding: 0;
  position: relative;
}

.browser-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.browser-gesture-hint {
  display: inline-flex;
  align-items: center;
}

.sample-selectors {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* ── Fancy selector buttons ────────────────────────────────────────────────── */
.fancy-selector-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px 5px 10px;
  border-radius: 8px;
  border: 1.5px solid rgba(13, 115, 119, 0.28);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 1px 4px rgba(13, 115, 119, 0.10), inset 0 1px 0 rgba(255,255,255,0.7);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, transform 0.12s ease;
  outline: none;
  font-family: var(--aa-font-sans);
  white-space: nowrap;
  min-width: 0;
}

.fancy-selector-btn:hover {
  border-color: rgba(13, 115, 119, 0.6);
  box-shadow: 0 2px 12px rgba(13, 115, 119, 0.20), inset 0 1px 0 rgba(255,255,255,0.8);
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.90);
}

.fancy-selector-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(13, 115, 119, 0.12);
}

/* Open (search) state */
.fancy-selector-btn--open {
  border-color: #0D7377;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(13, 115, 119, 0.12), 0 2px 8px rgba(13, 115, 119, 0.15);
  transform: none;
  cursor: default;
}

.fancy-selector-btn--open:hover {
  transform: none;
  border-color: #0D7377;
}

/* Inline search input (renders inside button when open) */
.fancy-btn-icon-search {
  color: #0D7377;
  flex-shrink: 0;
}

.fancy-btn-search-input {
  flex: 1;
  min-width: 80px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14.5px;
  font-family: var(--aa-font-sans);
  color: rgba(0, 0, 0, 0.87);
  line-height: 1.4;
  padding: 0;
}

.fancy-selector-btn--active {
  border-color: rgba(13, 115, 119, 0.75);
  background: rgba(13, 115, 119, 0.08);
  box-shadow: 0 2px 10px rgba(13, 115, 119, 0.22), inset 0 0 0 1px rgba(13, 115, 119, 0.15);
}

.fancy-selector-btn--active:hover {
  border-color: #0D7377;
  box-shadow: 0 3px 16px rgba(13, 115, 119, 0.32), inset 0 0 0 1px rgba(13, 115, 119, 0.20);
}

.fancy-btn-icon {
  display: flex;
  align-items: center;
  color: #0D7377;
  opacity: 0.85;
}

.fancy-btn-label {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--aa-slate-700);
}

.fancy-selector-btn--active .fancy-btn-label {
  color: #0D7377;
}

.fancy-btn-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 7px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.08);
  font-size: 12.5px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.55);
  min-width: 30px;
  line-height: 1.6;
  letter-spacing: 0.01em;
  transition: background 0.18s ease, color 0.18s ease;
}

.fancy-btn-badge--active {
  background: #0D7377;
  color: #ffffff;
}

.fancy-btn-chevron {
  color: rgba(0, 0, 0, 0.38);
  margin-left: -2px;
  transition: transform 0.18s ease;
}

.fancy-selector-btn--active .fancy-btn-chevron {
  color: #0D7377;
}

.selector-dropdown-card {
  border-radius: 8px !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.08) !important;
  overflow: hidden;
}

.selector-list {
  max-height: 260px;
  overflow-y: auto;
  padding: 0;
}

.selector-list-item {
  min-height: 36px;
  cursor: pointer;
}

.selector-list-item:hover {
  background: rgba(13, 115, 119, 0.06);
}
.browser-svg-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 16px;
  padding: 12px;
  background: #ffffff !important;
  border: 1px solid rgba(203, 213, 225, 0.72);
  touch-action: pan-x pan-y;
}

.genome-svg {
  display: block;
  cursor: grab;
  touch-action: pan-x pan-y;
}

.genome-svg:active {
  cursor: grabbing;
}

/* SVG element styling via classes */
:deep(.exon-box) {
  transition: opacity 0.15s ease, stroke 0.15s ease;
}

:deep(.apa-marker rect) {
  transition: fill-opacity 0.15s ease, width 0.15s ease;
}

@media (max-width: 900px) {
  .browser-svg-container {
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-x pan-y;
  }

  .genome-svg {
    min-width: 980px;
    cursor: default;
    touch-action: pan-x pan-y;
  }

  .browser-controls {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
}

@media (max-width: 640px) {
  .browser-svg-container {
    padding: 8px;
    border-radius: 12px;
  }

  .genome-svg {
    min-width: 760px;
  }
}
</style>
