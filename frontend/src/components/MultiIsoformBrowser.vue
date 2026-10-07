<template>
  <div class="multi-isoform-browser" :class="{ 'multi-isoform-browser--touch': isTouchLayout }">
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
        {{ isTouchLayout ? 'Swipe horizontally to inspect the full track' : 'Wheel to zoom • drag to pan' }}
      </span>
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
          <clipPath id="multi-iso-clip">
            <rect
              :x="margin.left"
              :y="0"
              :width="containerWidth - margin.left - margin.right"
              :height="totalHeight"
            />
          </clipPath>
        </defs>

        <!-- Labels group (fixed left) -->
        <g ref="labelsGroup" class="track-labels"></g>

        <!-- Ruler group -->
        <g ref="rulerGroup" class="ruler-track" clip-path="url(#multi-iso-clip)"></g>

        <!-- Per-isoform groups: exon track + apa track -->
        <g
          v-for="(tx, idx) in transcripts"
          :key="tx.transcript_id"
        >
          <g
            :ref="el => { if (el) exonGroupRefs[idx] = el }"
            class="exon-track"
            clip-path="url(#multi-iso-clip)"
          ></g>
          <g
            :ref="el => { if (el) apaGroupRefs[idx] = el }"
            class="apa-track"
            clip-path="url(#multi-iso-clip)"
          ></g>
        </g>
      </svg>
    </div>

    <!-- Statistics strip -->
    <div class="stats-strip mt-4">
      <v-row dense justify="center">
        <v-col cols="auto">
          <div class="stat-card">
            <div class="stat-value">{{ stats.totalSites }}</div>
            <div class="stat-label">Total Sites</div>
          </div>
        </v-col>
        <v-col cols="auto">
          <div class="stat-card stat-shared">
            <div class="stat-value" style="color: #A96F4C;">{{ stats.sharedSites }}</div>
            <div class="stat-label">Shared</div>
          </div>
        </v-col>
        <v-col cols="auto">
          <div class="stat-card stat-private">
            <div class="stat-value" style="color: #746A9E;">{{ stats.privateSites }}</div>
            <div class="stat-label">Private</div>
          </div>
        </v-col>
        <v-col cols="auto">
          <div class="stat-card">
            <div class="stat-value">{{ stats.isoforms }}</div>
            <div class="stat-label">Isoforms</div>
          </div>
        </v-col>
        <v-col cols="auto">
          <div class="stat-card">
            <div class="stat-value">{{ stats.sharingIndex }}</div>
            <div class="stat-label">Sharing Index</div>
          </div>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'

// Tooltip — single DOM node appended to body, positioned with fixed coords
let tooltipEl = null

const ensureTooltipEl = () => {
  if (!tooltipEl) {
    tooltipEl = document.createElement('div')
    tooltipEl.className = 'genome-tooltip-global'
    tooltipEl.style.cssText = `
      position: fixed;
      display: none;
      background: rgba(248,252,252,0.96);
      color: #0f172a;
      padding: 10px 13px;
      border: 1px solid rgba(13,115,119,0.18);
      border-radius: 12px;
      font-size: 13.5px;
      font-family: IBM Plex Sans, sans-serif;
      z-index: 99999;
      min-width: 190px;
      max-width: 280px;
      box-shadow: 0 18px 45px rgba(15,23,42,0.16);
      backdrop-filter: blur(16px) saturate(160%);
    `
    document.body.appendChild(tooltipEl)
  }
  return tooltipEl
}

const props = defineProps({
  geneData: { type: Object, required: true },
  transcriptStructures: { type: Object, required: true }
})

// ── Measure text width via offscreen canvas ──────────────────────────────────
const measureTextWidth = (text, fontSize = 13, fontWeight = '600') => {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  ctx.font = `${fontWeight} ${fontSize}px IBM Plex Sans, sans-serif`
  return ctx.measureText(text).width
}

// ── Dynamic left margin: widest label + padding ───────────────────────────────
const dynamicMarginLeft = computed(() => {
  // With two-line chromosome label the two lines are measured separately
  const labels = [
    'Chromosome',
    props.geneData?.chromosome ?? '',
    ...transcripts.value.map(tx => tx.transcript_id),
    ...transcripts.value
      .map(tx => formatRepresentativeStatus(transcriptRepresentativeStatus(tx)))
      .filter(Boolean),
    'PA Sites'
  ]
  const maxW = Math.max(...labels.map(l => measureTextWidth(l)))
  return Math.ceil(maxW) + 36  // 16px left + 20px right padding before separator
})

// ── Layout — margin.left is reactive ─────────────────────────────────────────
const margin = reactive({ top: 40, right: 16, bottom: 15, left: 150 })
const rulerHeight = 40
const trackPadding = 10
const labelWidth = computed(() => margin.left - 12)
const exonTrackHeight = 40
const apaTrackHeight = 40
const isoformGap = 12

// ── Colors ───────────────────────────────────────────────────────────────────
const SHARED_COLOR = '#A96F4C'
const PRIVATE_COLOR = '#746A9E'
const CDS_COLOR = '#0D7377'
const UTR_COLOR = '#14919B'
const INTRON_COLOR = '#B0B8C1'
const TERMINAL_EXTENSION_COLOR = '#5C8797'

const representativePriority = {
  MANE_Select: 1,
  RefSeq_Select: 2,
  Ensembl_Canonical: 3,
  APPRIS_Principal: 4
}

const transcriptRepresentativeStatus = (tx) => {
  const statuses = (tx?.apa_sites || [])
    .map(site => site.representative_status)
    .filter(status => status && status !== 'not_representative')
  if (!statuses.length) return null
  return statuses.sort((a, b) =>
    (representativePriority[a] || 99) - (representativePriority[b] || 99)
  )[0]
}

const formatRepresentativeStatus = (status) => {
  const labels = {
    MANE_Select: 'MANE Select',
    RefSeq_Select: 'RefSeq Select',
    Ensembl_Canonical: 'Ensembl Canonical',
    APPRIS_Principal: 'APPRIS Principal'
  }
  return labels[status] || status?.replace(/_/g, ' ')
}

const representativeBadgeStyle = (status) => {
  return {
    MANE_Select: {
      color: '#0f766e',
      background: 'rgba(240,253,250,0.88)',
      border: 'rgba(13,148,136,0.22)'
    },
    RefSeq_Select: {
      color: '#355c7d',
      background: 'rgba(241,245,249,0.95)',
      border: 'rgba(53,92,125,0.22)'
    },
    Ensembl_Canonical: {
      color: '#3f6f56',
      background: 'rgba(242,248,244,0.92)',
      border: 'rgba(63,111,86,0.22)'
    },
    APPRIS_Principal: {
      color: '#9a5b13',
      background: 'rgba(255,251,235,0.9)',
      border: 'rgba(194,120,25,0.24)'
    }
  }[status] || {
    color: '#475569',
    background: 'rgba(248,250,252,0.92)',
    border: 'rgba(100,116,139,0.22)'
  }
}

// ── Reactive state ───────────────────────────────────────────────────────────
const containerWidth = ref(1100)
const xScale = ref(null)
const zoomBehavior = ref(null)
const resizeObserver = ref(null)
const isTouchLayout = ref(false)

// Template refs
const browserContainer = ref(null)
const svgElement = ref(null)
const labelsGroup = ref(null)
const rulerGroup = ref(null)
const exonGroupRefs = ref([])
const apaGroupRefs = ref([])

// ── Computed data ─────────────────────────────────────────────────────────────
const transcripts = computed(() => props.geneData?.transcripts ?? [])

const siteTranscriptCount = computed(() => {
  const map = new Map()
  for (const tx of transcripts.value) {
    for (const site of tx.apa_sites ?? []) {
      map.set(site.unified_id, (map.get(site.unified_id) ?? 0) + 1)
    }
  }
  return map
})

const isShared = (siteId) => (siteTranscriptCount.value.get(siteId) ?? 0) >= 2

const genomicExtent = computed(() => {
  const positions = []
  for (const tx of transcripts.value) {
    const struct = props.transcriptStructures[tx.transcript_id]
    if (struct?.exons) {
      for (const e of struct.exons) { positions.push(e.start, e.end) }
    }
    for (const site of tx.apa_sites ?? []) {
      positions.push(site.mode_site_position)
    }
  }
  if (positions.length === 0) return [0, 1000]
  const min = Math.min(...positions)
  const max = Math.max(...positions)
  const pad = Math.max((max - min) * 0.15, 1000)
  return [min - pad, max + pad]
})

// Track Y offsets
const trackOffsets = computed(() => {
  const offsets = { ruler: margin.top, isoforms: [] }
  let y = margin.top + rulerHeight + trackPadding
  for (let i = 0; i < transcripts.value.length; i++) {
    offsets.isoforms.push({ exon: y, apa: y + exonTrackHeight + trackPadding })
    y += exonTrackHeight + trackPadding + apaTrackHeight + isoformGap
  }
  return offsets
})

const totalHeight = computed(() => {
  if (trackOffsets.value.isoforms.length === 0) {
    return margin.top + rulerHeight + margin.bottom + 20
  }
  const last = trackOffsets.value.isoforms[trackOffsets.value.isoforms.length - 1]
  return last.apa + apaTrackHeight + margin.bottom + 20
})

// ── Statistics ────────────────────────────────────────────────────────────────
const stats = computed(() => {
  const allSiteIds = new Set()
  for (const tx of transcripts.value) {
    for (const site of tx.apa_sites ?? []) allSiteIds.add(site.unified_id)
  }
  const totalSites = allSiteIds.size
  const sharedSites = [...allSiteIds].filter(id => isShared(id)).length
  const privateSites = totalSites - sharedSites
  const isoforms = transcripts.value.length
  const sharingIndex = totalSites > 0 ? (sharedSites / totalSites * 100).toFixed(1) + '%' : '0%'
  return { totalSites, sharedSites, privateSites, isoforms, sharingIndex }
})

// ── Helpers ───────────────────────────────────────────────────────────────────
// IGV-style coordinate formatting — unit chosen by visible range, not value magnitude
const formatCoordinate = (value) => {
  if (!xScale.value) return String(value)
  const domain = xScale.value.domain()
  const range = domain[1] - domain[0]

  if (range >= 1_000_000) {
    return (value / 1_000_000).toFixed(1) + ' Mb'
  } else if (range >= 10_000) {
    const dec = range < 100_000 ? 2 : 1
    return (value / 1_000).toFixed(dec) + ' Kb'
  } else if (range >= 1_000) {
    return (value / 1_000).toFixed(3) + ' Kb'
  } else {
    return Math.round(value).toLocaleString() + ' bp'
  }
}

const siteRange = (site) => {
  const fallback = Number(site?.mode_site_position)
  const start = site?.cluster_start != null ? Number(site.cluster_start) : fallback
  const end = site?.cluster_end != null ? Number(site.cluster_end) : fallback
  return {
    start: Math.min(start, end),
    end: Math.max(start, end),
  }
}

const terminalExtensionFor = (tx, sortedExons, strand) => {
  if (!sortedExons.length) return null

  const terminalExon = strand === '-' ? sortedExons[0] : sortedExons[sortedExons.length - 1]
  const ranges = (tx.apa_sites ?? []).map(siteRange).filter(r =>
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
  el.style.borderRadius = '6px'
  el.style.background = 'rgba(33,37,41,0.95)'
  el.style.backdropFilter = 'blur(4px)'
  el.style.webkitBackdropFilter = 'blur(4px)'
  el.style.border = 'none'
  el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.35)'
  el.style.color = '#fff'
  el.style.minWidth = '190px'
  el.style.maxWidth = '280px'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const clientX = nativeEvent.clientX
  const clientY = nativeEvent.clientY

  const OFFSET_X = 14
  const OFFSET_Y = -10
  const W = el.offsetWidth || 220
  const H = el.offsetHeight || 120
  const vw = window.innerWidth
  const vh = window.innerHeight

  let x = clientX + OFFSET_X
  let y = clientY + OFFSET_Y

  if (x + W > vw - 8) x = clientX - W - OFFSET_X
  if (y + H > vh - 8) y = clientY - H - Math.abs(OFFSET_Y)
  if (y < 4) y = 4
  if (x < 4) x = 4

  el.style.left = x + 'px'
  el.style.top  = y + 'px'
}

const showApaTooltip = (event, site, classification, meanAbundance, sampleDetails, txSamples) => {
  const el = ensureTooltipEl()

  const pct = (meanAbundance * 100).toFixed(1)
  const classColor = classification === 'Shared'
    ? { bg: 'rgba(169,111,76,0.11)', border: 'rgba(169,111,76,0.30)', text: '#87563A' }
    : { bg: 'rgba(116,106,158,0.11)', border: 'rgba(116,106,158,0.30)', text: '#5F5682' }

  const detectedSet = new Set(sampleDetails.map(d => d.sample_name ?? d.sample ?? ''))
  const totalN = txSamples.length || detectedSet.size
  const detected = detectedSet.size || sampleDetails.length
  const coveragePct = totalN > 0 ? (detected / totalN) * 100 : 0

  // Donut ring — r=24, SW=5 → inner clear radius = 21.5px
  const R = 24, SW = 5
  const circ = 2 * Math.PI * R
  const dash = (coveragePct / 100) * circ
  const gap = circ - dash
  const cx = 32, cy = 32, size = 64

  const ringColor = coveragePct === 100 ? '#355C7D' : coveragePct >= 50 ? '#4A7898' : PRIVATE_COLOR
  const tagLine = coveragePct === 100 ? 'in every sample'
    : coveragePct >= 75 ? 'in most samples'
    : coveragePct >= 50 ? 'in half the samples'
    : 'in a few samples'

  const donutSvg = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="flex-shrink:0;display:block">
      <circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="rgba(99,102,241,0.15)" stroke-width="${SW}"/>
      <circle cx="${cx}" cy="${cy}" r="${R}" fill="none"
        stroke="${ringColor}" stroke-width="${SW}"
        stroke-dasharray="${dash.toFixed(2)} ${gap.toFixed(2)}"
        stroke-linecap="round"
        transform="rotate(-90 ${cx} ${cy})"/>
      <text x="${cx}" y="${cy - 4}" text-anchor="middle" dominant-baseline="auto"
        style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;font-weight:800;fill:${ringColor}"
      >${detected}</text>
      <line x1="${cx - 7}" y1="${cy + 1}" x2="${cx + 7}" y2="${cy + 1}" stroke="rgba(99,102,241,0.30)" stroke-width="0.8"/>
      <text x="${cx}" y="${cy + 12}" text-anchor="middle" dominant-baseline="auto"
        style="font-family:'IBM Plex Sans',sans-serif;font-size:9px;font-weight:600;fill:#94a3b8"
      >${totalN}</text>
    </svg>`

  el.innerHTML = `
    <div style="padding:13px 15px">
      <div style="font-size:10.5px;letter-spacing:0.10em;color:#0D7377;font-weight:700;text-transform:uppercase;margin-bottom:3px">PA Site</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:11.5px;color:#0f172a;word-break:break-all;line-height:1.5;font-weight:600;margin-bottom:10px">${site.unified_id}</div>
      <div style="height:1px;background:rgba(13,115,119,0.15);margin-bottom:9px"></div>
      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Rep. Position</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${site.mode_site_position.toLocaleString()}</span>
        <span style="color:#475569;font-size:12.5px">Classification</span>
        <span style="display:inline-block;padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:600;background:${classColor.bg};border:1px solid ${classColor.border};color:${classColor.text};letter-spacing:0.03em;justify-self:start;white-space:nowrap">${classification}</span>
        <span style="color:#475569;font-size:12.5px">Mean Abundance</span>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:60px;height:5px;background:rgba(13,115,119,0.15);border-radius:3px;overflow:hidden">
            <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#0D7377,#14919B);border-radius:3px"></div>
          </div>
          <span style="color:#0D7377;font-size:12.5px;font-weight:700;font-family:'IBM Plex Sans',sans-serif">${pct}%</span>
        </div>
      </div>

      <div style="height:1px;background:rgba(13,115,119,0.15);margin:10px 0 9px"></div>

      <div style="background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.18);border-radius:8px;padding:9px 11px;display:flex;align-items:center;gap:12px">
        ${donutSvg}
        <div>
          <div style="font-family:'IBM Plex Sans',sans-serif;font-size:13px;font-weight:700;color:#0f172a;line-height:1.3">
            <span style="color:${ringColor};font-size:16px;font-weight:800">${detected}</span>
            <span style="color:#94a3b8;font-size:12px;font-weight:500"> / ${totalN} samples</span>
          </div>
          <div style="font-size:11px;color:#64748b;margin-top:3px">${tagLine}</div>
        </div>
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

const showExonTooltip = (event, displayNum, exon, txId) => {
  const el = ensureTooltipEl()

  el.innerHTML = `
    <div style="padding:13px 15px">
      <div style="font-size:10.5px;letter-spacing:0.10em;color:#0D7377;font-weight:700;text-transform:uppercase;margin-bottom:3px">Exon</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:14px;color:#0f172a;font-weight:700;margin-bottom:10px">Exon ${displayNum}</div>
      <div style="height:1px;background:rgba(13,115,119,0.15);margin-bottom:9px"></div>
      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Transcript</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:600;font-family:'IBM Plex Sans',sans-serif">${txId}</span>
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
  el.style.minWidth = '220px'
  el.style.maxWidth = '300px'
  el.style.fontSize = '13px'
  el.style.fontFamily = 'IBM Plex Sans, sans-serif'
  el.style.color = '#0f172a'
  el.style.display = 'block'

  const nativeEvent = event.sourceEvent || event
  const W = el.offsetWidth || 240
  const H = el.offsetHeight || 140
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

const showTerminalExtensionTooltip = (event, extension, txId) => {
  const el = ensureTooltipEl()
  const length = Math.abs(extension.end - extension.start)

  el.innerHTML = `
    <div style="padding:13px 15px">
      <div style="font-size:10.5px;letter-spacing:0.10em;color:#B7791F;font-weight:700;text-transform:uppercase;margin-bottom:3px">APA-supported extension</div>
      <div style="font-family:'IBM Plex Sans',sans-serif;font-size:14px;color:#0f172a;font-weight:700;margin-bottom:10px">Terminal exon extension</div>
      <div style="height:1px;background:rgba(183,121,31,0.20);margin-bottom:9px"></div>
      <div style="display:grid;grid-template-columns:auto 1fr;row-gap:6px;column-gap:16px;align-items:center">
        <span style="color:#475569;font-size:12.5px;white-space:nowrap">Transcript</span>
        <span style="color:#0f172a;font-size:12.5px;font-weight:600;font-family:'IBM Plex Sans',sans-serif">${txId}</span>
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

const hideTooltip = () => {
  if (tooltipEl) tooltipEl.style.display = 'none'
}

// ── Render: ruler ─────────────────────────────────────────────────────────────
const renderRuler = () => {
  const g = d3.select(rulerGroup.value)
  g.selectAll('*').remove()
  g.attr('transform', `translate(0, ${trackOffsets.value.ruler})`)

  g.append('rect')
    .attr('x', margin.left).attr('y', 0)
    .attr('width', containerWidth.value - margin.left - margin.right)
    .attr('height', rulerHeight)
    .attr('fill', '#FAFBFC')
    .attr('stroke', 'rgba(0,0,0,0.12)').attr('stroke-width', 1)

  const domain = xScale.value.domain()
  const visibleRange = domain[1] - domain[0]
  const trackWidth = containerWidth.value - margin.left - margin.right

  const sampleLabel = formatCoordinate((domain[0] + domain[1]) / 2)
  const labelPx = measureTextWidth(sampleLabel, 12, '500')
  const minSpacingPx = labelPx + 40

  const maxTicks = Math.max(2, Math.floor(trackWidth / minSpacingPx))

  const rawStep = visibleRange / maxTicks
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const factor = rawStep / magnitude
  const niceStep = factor < 1.5 ? magnitude
    : factor < 3.5 ? 2 * magnitude
    : factor < 7.5 ? 5 * magnitude
    : 10 * magnitude

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

  axisGroup.selectAll('.domain').attr('stroke', 'rgba(0,0,0,0.2)').attr('stroke-width', 1)
  axisGroup.selectAll('line').attr('stroke', '#999')
  axisGroup.selectAll('text')
    .style('font-family', 'IBM Plex Sans, sans-serif')
    .style('font-size', '12px')
    .style('font-weight', '500')
    .style('fill', 'rgba(0,0,0,0.6)')
    .attr('dy', '-5px')
}

// ── Render: labels ────────────────────────────────────────────────────────────
const renderLabels = () => {
  const g = d3.select(labelsGroup.value)
  g.selectAll('*').remove()

  // Chromosome label — two lines, horizontally centered: "Chromosome" (muted) above ID (teal)
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
    .text(props.geneData?.chromosome ?? '')

  // Per-isoform labels
  transcripts.value.forEach((tx, i) => {
    const offsets = trackOffsets.value.isoforms[i]
    const representativeStatus = transcriptRepresentativeStatus(tx)
    const representativeLabel = formatRepresentativeStatus(representativeStatus)

    // Exon track label — full transcript ID, centered in left column
    g.append('text')
      .attr('x', labelWidth.value / 2)
      .attr('y', offsets.exon + (representativeLabel ? 13 : exonTrackHeight / 2))
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .style('font-family', 'IBM Plex Sans, sans-serif')
      .style('font-size', '13.5px')
      .style('font-weight', '600')
      .style('fill', CDS_COLOR)
      .text(tx.transcript_id)

    if (representativeLabel) {
      const badgeStyle = representativeBadgeStyle(representativeStatus)
      const badgeFontSize = 9.5
      const badgePaddingX = 6
      const badgePaddingY = 1
      const badgeTextWidth = measureTextWidth(representativeLabel, badgeFontSize, '600')
      const badgeWidth = Math.ceil(badgeTextWidth + badgePaddingX * 2)
      const badgeHeight = Math.ceil(badgeFontSize * 1.15 + badgePaddingY * 2)
      const badgeX = labelWidth.value / 2 - badgeWidth / 2
      const badgeY = offsets.exon + 24

      g.append('rect')
        .attr('x', badgeX)
        .attr('y', badgeY)
        .attr('width', badgeWidth)
        .attr('height', badgeHeight)
        .attr('rx', badgeHeight / 2)
        .attr('ry', badgeHeight / 2)
        .attr('fill', badgeStyle.background)
        .attr('stroke', badgeStyle.border)
        .attr('stroke-width', 1)

      g.append('text')
        .attr('x', labelWidth.value / 2)
        .attr('y', badgeY + badgeHeight / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-family', 'IBM Plex Sans, sans-serif')
        .style('font-size', `${badgeFontSize}px`)
        .style('font-weight', '600')
        .style('letter-spacing', '0.02em')
        .style('fill', badgeStyle.color)
        .text(representativeLabel)
    }

    // APA track label — centered in left column
    g.append('text')
      .attr('x', labelWidth.value / 2)
      .attr('y', offsets.apa + apaTrackHeight / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .style('font-family', 'IBM Plex Sans, sans-serif')
      .style('font-size', '12.5px')
      .style('font-weight', '600')
      .style('fill', '#475569')
      .text('PA Sites')
  })

  // Vertical separator
  g.append('line')
    .attr('x1', margin.left - 5).attr('x2', margin.left - 5)
    .attr('y1', trackOffsets.value.ruler)
    .attr('y2', totalHeight.value - margin.bottom)
    .attr('stroke', 'rgba(0,0,0,0.12)').attr('stroke-width', 1)
}

// ── Render: single exon track ─────────────────────────────────────────────────
const renderExonTrack = (txIndex) => {
  const tx = transcripts.value[txIndex]
  const g = d3.select(exonGroupRefs.value[txIndex])
  if (!g || !g.node()) return
  g.selectAll('*').remove()

  const offsets = trackOffsets.value.isoforms[txIndex]
  g.attr('transform', `translate(0, ${offsets.exon})`)

  const trackY = exonTrackHeight / 2
  const struct = props.transcriptStructures[tx.transcript_id]

  // Track background
  g.append('rect')
    .attr('x', margin.left).attr('y', 0)
    .attr('width', containerWidth.value - margin.left - margin.right)
    .attr('height', exonTrackHeight)
    .attr('fill', txIndex % 2 === 0 ? '#FFFFFF' : '#FAFBFC')
    .attr('stroke', 'rgba(0,0,0,0.12)').attr('stroke-width', 1)

  if (!struct?.exons?.length) return

  const sortedExons = [...struct.exons].sort((a, b) => a.start - b.start)
  const cdsSet = new Set((struct.cds ?? []).map(c => `${c.start}-${c.end}`))
  const strand = props.geneData?.strand ?? '+'
  const terminalExtension = terminalExtensionFor(tx, sortedExons, strand)

  // Intron backbone
  if (sortedExons.length > 1) {
    const bx1 = xScale.value(sortedExons[0].start)
    const bx2 = xScale.value(sortedExons[sortedExons.length - 1].end)
    g.append('line')
      .attr('x1', bx1).attr('x2', bx2)
      .attr('y1', trackY).attr('y2', trackY)
      .attr('stroke', INTRON_COLOR).attr('stroke-width', 2)

    // Chevrons
    for (let i = 0; i < sortedExons.length - 1; i++) {
      const ix1 = xScale.value(sortedExons[i].end)
      const ix2 = xScale.value(sortedExons[i + 1].start)
      const iw = ix2 - ix1
      if (iw > 20) {
        const num = Math.max(1, Math.floor(iw / 40))
        const sp = iw / (num + 1)
        const cs = 4
        for (let j = 1; j <= num; j++) {
          const ax = ix1 + j * sp
          const path = strand === '+'
            ? `M${ax - cs},${trackY - cs} L${ax + cs},${trackY} L${ax - cs},${trackY + cs}`
            : `M${ax + cs},${trackY - cs} L${ax - cs},${trackY} L${ax + cs},${trackY + cs}`
          g.append('path').attr('d', path)
            .attr('fill', 'none').attr('stroke', '#999')
            .attr('stroke-width', 1.5).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round')
        }
      }
    }
  }

  if (terminalExtension) {
    const x1 = xScale.value(terminalExtension.start)
    const x2 = xScale.value(terminalExtension.end)
    const x = Math.min(x1, x2)
    const w = Math.max(3, Math.abs(x2 - x1))
    const exonH = 20
    const extensionStroke = 1
    const extensionH = exonH - extensionStroke * 2

    const ext = g.append('g')
      .attr('class', 'terminal-extension')
      .style('cursor', 'help')

    ext.append('rect')
      .attr('x', x).attr('y', trackY - extensionH / 2)
      .attr('width', w).attr('height', extensionH)
      .attr('fill', TERMINAL_EXTENSION_COLOR)
      .attr('fill-opacity', 0.16)
      .attr('stroke', TERMINAL_EXTENSION_COLOR)
      .attr('stroke-width', extensionStroke)
      .attr('stroke-dasharray', '4,3')
      .attr('rx', 3)

    ext.append('rect')
      .attr('x', x).attr('y', 0)
      .attr('width', w).attr('height', exonTrackHeight)
      .attr('fill', 'transparent')

    if (w > 72) {
      ext.append('text')
        .attr('x', x + w / 2).attr('y', trackY)
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
        showTerminalExtensionTooltip(event, terminalExtension, tx.transcript_id)
      })
      .on('mousemove', function(event) {
        showTerminalExtensionTooltip(event, terminalExtension, tx.transcript_id)
      })
      .on('mouseleave', function() {
        d3.select(this).select('rect').attr('fill-opacity', 0.16)
        hideTooltip()
      })
  }

  // Exons
  sortedExons.forEach((exon, idx) => {
    const displayNum = strand === '-' ? sortedExons.length - idx : idx + 1
    const isCDS = cdsSet.has(`${exon.start}-${exon.end}`)
    const exonH = 20
    const exonColor = isCDS ? CDS_COLOR : UTR_COLOR
    const x = xScale.value(exon.start)
    const w = Math.max(3, xScale.value(exon.end) - x)

    g.append('rect')
      .attr('class', 'exon-box')
      .attr('x', x).attr('y', trackY - exonH / 2)
      .attr('width', w).attr('height', exonH)
      .attr('fill', exonColor)
      .attr('stroke', '#fff').attr('stroke-width', 1.5).attr('rx', 3)
      .style('cursor', 'pointer')
      .on('mouseenter', function(event) {
        d3.select(this).attr('opacity', 0.8).attr('stroke', '#000')
        showExonTooltip(event, displayNum, exon, tx.transcript_id)
      })
      .on('mousemove', function(event) {
        showExonTooltip(event, displayNum, exon, tx.transcript_id)
      })
      .on('mouseleave', function() {
        d3.select(this).attr('opacity', 1).attr('stroke', '#fff')
        hideTooltip()
      })

    if (w > 30) {
      g.append('text')
        .attr('x', x + w / 2).attr('y', trackY).attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '11px').style('font-weight', '600')
        .style('fill', '#fff').style('pointer-events', 'none')
        .text(displayNum)
    }
  })
}

// ── Render: single APA track ──────────────────────────────────────────────────
const renderApaTrack = (txIndex) => {
  const tx = transcripts.value[txIndex]
  const g = d3.select(apaGroupRefs.value[txIndex])
  if (!g || !g.node()) return
  g.selectAll('*').remove()

  const offsets = trackOffsets.value.isoforms[txIndex]
  g.attr('transform', `translate(0, ${offsets.apa})`)

  const trackY = apaTrackHeight
  const maxCurveH = trackY - 4
  const MIN_HALF_PX = 8

  // Track background
  g.append('rect')
    .attr('x', margin.left).attr('y', 0)
    .attr('width', containerWidth.value - margin.left - margin.right)
    .attr('height', apaTrackHeight)
    .attr('fill', txIndex % 2 === 0 ? '#FAFBFC' : '#FFFFFF')
    .attr('stroke', 'rgba(0,0,0,0.12)').attr('stroke-width', 1)

  for (const site of tx.apa_sites ?? []) {
    const sampleDetails = site.sample_details ?? []
    const meanAbundance = sampleDetails.length > 0
      ? sampleDetails.reduce((s, d) => s + d.site_abundance, 0) / sampleDetails.length
      : 1
    const color = isShared(site.unified_id) ? SHARED_COLOR : PRIVATE_COLOR
    const classification = isShared(site.unified_id) ? 'Shared' : 'Private'

    const xRep = xScale.value(site.mode_site_position)

    let xStart, xEnd
    if (site.cluster_start != null && site.cluster_end != null) {
      const gStart = Number(site.cluster_start)
      const gEnd = Number(site.cluster_end)
      xStart = gStart === gEnd ? xRep - MIN_HALF_PX : Math.min(xScale.value(gStart), xRep - MIN_HALF_PX)
      xEnd   = gStart === gEnd ? xRep + MIN_HALF_PX : Math.max(xScale.value(gEnd),   xRep + MIN_HALF_PX)
    } else {
      // Backward-compatible fallback for legacy IDs formatted as chr:start-end:strand.
      const rangeMatch = site.unified_id.match(/:(\d+)-(\d+):/)
      if (rangeMatch) {
        const gStart = parseInt(rangeMatch[1])
        const gEnd = parseInt(rangeMatch[2])
        xStart = gStart === gEnd ? xRep - MIN_HALF_PX : Math.min(xScale.value(gStart), xRep - MIN_HALF_PX)
        xEnd   = gStart === gEnd ? xRep + MIN_HALF_PX : Math.max(xScale.value(gEnd),   xRep + MIN_HALF_PX)
      } else {
        xStart = xRep - MIN_HALF_PX
        xEnd   = xRep + MIN_HALF_PX
      }
    }

    const sigmaL = (xRep - xStart) / 2.5
    const sigmaR = (xEnd  - xRep)  / 2.5
    const peakH  = Math.max(4, meanAbundance * maxCurveH)

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
    const areaPath = `M ${xStart} ${trackY} ` +
      pts.map(([px, py]) => `L ${px} ${py}`).join(' ') +
      ` L ${xEnd} ${trackY} Z`

    const marker = g.append('g').attr('class', 'apa-marker').style('cursor', 'pointer')

    // Filled area
    marker.append('path')
      .attr('d', areaPath)
      .attr('fill', color)
      .attr('fill-opacity', 0.18)
      .attr('stroke', 'none')

    // Curve outline
    marker.append('path')
      .attr('d', curvePath)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.85)

    // Dashed vertical at representative position
    marker.append('line')
      .attr('x1', xRep).attr('x2', xRep)
      .attr('y1', trackY - peakH).attr('y2', trackY)
      .attr('stroke', color)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '2,2')
      .attr('stroke-opacity', 0.7)

    // Invisible hit area
    marker.append('rect')
      .attr('x', xStart).attr('y', 0)
      .attr('width', Math.max(12, xEnd - xStart))
      .attr('height', apaTrackHeight)
      .attr('fill', 'transparent')

    marker
      .on('mouseenter', function(event) {
        d3.select(this).select('path:nth-child(2)').attr('stroke-width', 2.5).attr('stroke-opacity', 1)
        d3.select(this).select('path:first-child').attr('fill-opacity', 0.32)
        showApaTooltip(event, site, classification, meanAbundance, sampleDetails, tx.samples ?? [])
      })
      .on('mousemove', function(event) {
        showApaTooltip(event, site, classification, meanAbundance, sampleDetails, tx.samples ?? [])
      })
      .on('mouseleave', function() {
        d3.select(this).select('path:nth-child(2)').attr('stroke-width', 1.5).attr('stroke-opacity', 0.85)
        d3.select(this).select('path:first-child').attr('fill-opacity', 0.18)
        hideTooltip()
      })
  }
}
// ── Full render ───────────────────────────────────────────────────────────────
const render = () => {
  if (!svgElement.value) return
  initScale()
  renderLabels()
  renderRuler()
  transcripts.value.forEach((_, i) => {
    renderExonTrack(i)
    renderApaTrack(i)
  })
}

const renderTracks = () => {
  renderRuler()
  transcripts.value.forEach((_, i) => {
    renderExonTrack(i)
    renderApaTrack(i)
  })
}

// ── Scale init ────────────────────────────────────────────────────────────────
const initScale = () => {
  // Map content bounds (all exon + APA positions + 5% pad) directly to the track.
  // k=1 always equals "full-content fit", so scaleExtent([1,100]) and translateExtent
  // work correctly without any fitK gymnastics — same approach as ApaGenomeBrowser.
  const positions = []
  for (const tx of transcripts.value) {
    const struct = props.transcriptStructures[tx.transcript_id]
    if (struct?.exons) {
      for (const e of struct.exons) { positions.push(e.start, e.end) }
    }
    for (const site of tx.apa_sites ?? []) {
      positions.push(site.mode_site_position)
    }
  }
  const cMin = positions.length ? Math.min(...positions) : 0
  const cMax = positions.length ? Math.max(...positions) : 1000
  const span = cMax - cMin
  const pad = span * 0.05
  xScale.value = d3.scaleLinear()
    .domain([cMin - pad, cMax + pad])
    .range([margin.left, containerWidth.value - margin.right])
}

// ── Zoom ──────────────────────────────────────────────────────────────────────
let _frozenBaseScale = null

function shouldHandleZoomEvent(event) {
  // Let one-finger touch gestures scroll the page. D3 handles desktop wheel/drag
  // and two-finger pinch gestures for horizontal zoom/pan inside the track panel.
  if (event.type?.startsWith('touch')) {
    if (event.type === 'touchend' || event.type === 'touchcancel') {
      return !!this.__zooming
    }
    return (event.touches?.length ?? 0) >= 2
  }
  return true
}

const setupZoom = () => {
  if (isTouchLayout.value) {
    zoomBehavior.value = null
    d3.select(svgElement.value).on('.zoom', null)
    return
  }

  const baseScale = xScale.value.copy()  // Snapshot of base (k=1) scale — never mutated
  _frozenBaseScale = baseScale

  const trackLeft = margin.left
  const trackRight = containerWidth.value - margin.right

  // translateExtent locks content endpoints to track edges — user can never pan
  // the transcript off-screen. Combined with scaleExtent([1,100]), zooming out to
  // minimum always restores the full-fit view regardless of current pan position.
  zoomBehavior.value = d3.zoom()
    .filter(shouldHandleZoomEvent)
    .scaleExtent([1, 100])
    .translateExtent([[trackLeft, -Infinity], [trackRight, Infinity]])
    .extent([[trackLeft, 0], [trackRight, totalHeight.value]])
    .on('zoom', (event) => {
      xScale.value = event.transform.rescaleX(baseScale)
      renderTracks()
    })

  d3.select(svgElement.value).call(zoomBehavior.value)
  // k=1 identity transform is the fit view
  d3.select(svgElement.value).call(zoomBehavior.value.transform, d3.zoomIdentity)
}

const zoomIn = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  d3.select(svgElement.value).transition().duration(300).call(zoomBehavior.value.scaleBy, 1.5)
}

const zoomOut = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  d3.select(svgElement.value).transition().duration(300).call(zoomBehavior.value.scaleBy, 0.67)
}

const resetZoom = () => {
  if (!zoomBehavior.value || isTouchLayout.value) return
  d3.select(svgElement.value).transition().duration(500).call(zoomBehavior.value.transform, d3.zoomIdentity)
}

// ── Width measurement ─────────────────────────────────────────────────────────
const measureWidth = () => {
  if (browserContainer.value) {
    const previousTouchLayout = isTouchLayout.value
    const visibleWidth = Math.floor(browserContainer.value.getBoundingClientRect().width - 24)
    if (visibleWidth <= 0) return

    const mobile = window.matchMedia('(max-width: 640px)').matches
    const tablet = window.matchMedia('(max-width: 900px)').matches
    const coarsePointer = window.matchMedia('(pointer: coarse)').matches
    const hoverless = window.matchMedia('(hover: none)').matches
    isTouchLayout.value = tablet && (coarsePointer || hoverless)

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

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(() => {
  nextTick(() => {
    measureWidth()
    if (transcripts.value.length > 0) {
      render()
      setupZoom()
    }
    resizeObserver.value = new ResizeObserver(() => {
      const interactionModeChanged = measureWidth()
      if (transcripts.value.length > 0) {
        render()
        if (interactionModeChanged) setupZoom()
      }
    })
    if (browserContainer.value) resizeObserver.value.observe(browserContainer.value)
  })
})

onBeforeUnmount(() => {
  resizeObserver.value?.disconnect()
  if (tooltipEl) {
    tooltipEl.remove()
    tooltipEl = null
  }
})

watch(
  () => [props.geneData, props.transcriptStructures],
  () => {
    nextTick(() => {
      if (transcripts.value.length > 0) {
        render()
        setupZoom()
      }
    })
  },
  { deep: true }
)

// Sync margin.left whenever dynamic label width changes, then re-render
watch(dynamicMarginLeft, (newLeft) => {
  margin.left = newLeft
  nextTick(() => { if (transcripts.value.length > 0) render() })
}, { immediate: true })
</script>

<style scoped>
.multi-isoform-browser {
  width: 100%;
  background: transparent;
  border-radius: 8px;
  padding: 0;
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

.browser-svg-container {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: 16px;
  padding: 12px;
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

/* Statistics strip */
.stats-strip {
  border-top: 1px solid rgba(13, 115, 119, 0.15);
  padding-top: 16px;
}

.stat-card {
  text-align: center;
  padding: 8px 20px;
  border-radius: 12px;
  background: rgba(13, 115, 119, 0.04);
  border: 1px solid rgba(13, 115, 119, 0.15);
  min-width: 90px;
}

.stat-shared {
  background: rgba(169, 111, 76, 0.10);
  border-color: rgba(169, 111, 76, 0.26);
}

.stat-private {
  background: rgba(116, 106, 158, 0.10);
  border-color: rgba(116, 106, 158, 0.26);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
  font-family: var(--aa-font-display);
}

.stat-label {
  font-size: 12px;
  color: #475569;
  font-weight: 700;
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: var(--aa-font-display);
}

:deep(.exon-box) {
  transition: opacity 0.15s ease, stroke 0.15s ease;
}

:deep(.apa-marker line) {
  transition: stroke-width 0.15s ease;
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

  .stats-strip :deep(.v-row) {
    justify-content: flex-start !important;
    overflow-x: auto;
    flex-wrap: nowrap;
    padding-bottom: 4px;
  }

  .stat-card {
    min-width: 96px;
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

  .stat-card {
    padding: 7px 14px;
  }

  .stat-value {
    font-size: 20px;
  }
}
</style>
