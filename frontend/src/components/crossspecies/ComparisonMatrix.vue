<template>
  <section class="section-card matrix-card">
    <div class="matrix-head">
      <div class="section-eyebrow">Comparative overview</div>
      <h2>PAS overview</h2>
      <p>Observed transcripts and unique PASs across the available sample groups.</p>
    </div>

    <div class="matrix-wrap">
      <table class="matrix-table">
        <thead>
          <tr>
            <th scope="col" class="matrix-colhead">Species / Gene</th>
            <th v-for="metric in METRICS" :key="metric.key" scope="col" class="matrix-colhead">
              {{ metric.title }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.gene_db_id">
            <th scope="row" class="matrix-leader">
              <span class="matrix-species">{{ row.scientific_name }}</span>
              <router-link :to="row.detailRoute" class="matrix-gene">{{ row.gene_name }}</router-link>
              <span class="matrix-locus">{{ row.chromosome }} · {{ row.strand }}</span>
            </th>
            <td
              v-for="cell in row.cells"
              :key="cell.key"
              class="matrix-cell"
              :class="{ 'is-missing': cell.missing }"
            >
              <span class="matrix-value" :title="cell.missing ? cell.missingHint : null">
                {{ cell.display }}
              </span>
              <span class="matrix-track" aria-hidden="true">
                <span class="matrix-bar" :style="{ width: cell.barWidth }"></span>
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { computed, watchEffect } from 'vue'
import { formatCount } from '@/utils/pasLayout'

const props = defineProps({
  genes: { type: Array, default: () => [] }
})

/**
 * Rendered when a metric field is absent from the API payload. An explicit
 * marker keeps a backend rename visible instead of silently blanking a cell.
 */
const MISSING_DISPLAY = '—'

/**
 * Single source of truth for the matrix columns. `field` names the API property,
 * `format` only ever receives a finite number (missing values never reach it).
 */
const METRICS = Object.freeze([
  {
    key: 'sample_count',
    field: 'sample_count',
    title: 'Sample groups',
    format: value => formatCount(value)
  },
  {
    key: 'transcript_count',
    field: 'transcript_count',
    title: 'Transcripts',
    format: value => formatCount(value)
  },
  {
    key: 'pa_site_count',
    field: 'pa_site_count',
    title: 'Unique PA sites',
    format: value => formatCount(value)
  },
  {
    key: 'mean_pa_sites_per_transcript',
    field: 'mean_pa_sites_per_transcript',
    title: 'PA sites / transcript',
    format: value => value.toFixed(2)
  },
  {
    key: 'multi_pas_transcript_pct',
    field: 'multi_pas_transcript_pct',
    title: 'Multi-PAS transcripts',
    format: value => `${value}%`
  }
])

/** Returns a finite number, or null when the field is absent/unparseable. */
const readMetric = (gene, metric) => {
  const raw = gene?.[metric.field]
  if (raw === null || raw === undefined || raw === '') return null
  const value = Number(raw)
  return Number.isFinite(value) ? value : null
}

/** Fields declared in METRICS that no gene in the payload actually provides. */
const missingFields = computed(() =>
  props.genes.length
    ? METRICS.filter(metric =>
        props.genes.every(gene => readMetric(gene, metric) === null)
      ).map(metric => metric.field)
    : []
)

watchEffect(() => {
  if (missingFields.value.length) {
    console.warn(
      `[ComparisonMatrix] No gene in the payload provides: ${missingFields.value.join(', ')}. ` +
        'The backend field names may have changed.'
    )
  }
})

/** Per-column maxima — metrics have incomparable units, so scaling stays per column. */
const columnMax = computed(() =>
  Object.fromEntries(
    METRICS.map(metric => {
      const values = props.genes
        .map(gene => readMetric(gene, metric))
        .filter(value => value !== null)
      return [metric.key, values.length ? Math.max(0, ...values) : 0]
    })
  )
)

const rows = computed(() =>
  props.genes.map(gene => ({
    ...gene,
    detailRoute: {
      name: 'GeneDetail',
      params: { geneId: gene.gene_db_id },
      query: { species: gene.species }
    },
    cells: METRICS.map(metric => {
      const value = readMetric(gene, metric)
      const max = columnMax.value[metric.key]
      const ratio = value !== null && max > 0 ? value / max : 0
      return {
        key: metric.key,
        missing: value === null,
        missingHint: `No "${metric.field}" value was returned for this gene.`,
        display: value === null ? MISSING_DISPLAY : metric.format(value),
        // Percentage of the track, not of the cell — see .matrix-track below.
        barWidth: `${(ratio * 100).toFixed(3)}%`
      }
    })
  }))
)
</script>

<style scoped>
.matrix-card {
  padding: 24px;
  border-radius: var(--aa-radius-xl, 22px);
  overflow: hidden;
}
.matrix-head h2 {
  margin: 10px 0 7px;
  color: var(--aa-slate-800, #1e293b);
  font-size: var(--compare-title-size, 1.38rem);
  font-weight: 600;
  line-height: 1.3;
}
.matrix-head p { margin: 0; color: var(--aa-slate-500); font-size: var(--compare-body-size); line-height: 1.55; }

.matrix-wrap {
  margin-top: 20px;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(13, 115, 119, 0.36) rgba(226, 232, 240, 0.55);
}
.matrix-table { width: 100%; border-collapse: collapse; }
.matrix-table th,
.matrix-table td { padding: 12px 14px; text-align: left; }

/*
 * Column headers: mirrors the Search.vue `.search-frame-topbar` + `.topbar-label`
 * treatment (teal gradient band, display font, 0.12em tracking). `!important` is
 * required to beat the global `table th { ... !important }` rule in visual-system.css.
 */
.matrix-table thead th.matrix-colhead {
  background: #f4f8f9 !important;
  border-bottom: 1px solid rgba(13, 115, 119, 0.10) !important;
  color: var(--aa-slate-600, #475569) !important;
  font-family: var(--aa-font-display, 'IBM Plex Sans', sans-serif) !important;
  font-size: 0.76rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
  white-space: nowrap;
}

.matrix-table tbody tr { border-bottom: 1px solid rgba(226, 232, 240, 0.85); }
.matrix-table tbody tr:last-child { border-bottom: 0; }

/*
 * Row headers hold species binomials, which must keep their mandated
 * capitalisation (genus capitalised, epithet lower-case, italicised). The global
 * `table th` rule in visual-system.css targets column headers but also matches
 * these `<th scope="row">` cells, so every inherited declaration is reverted here.
 * Specificity: `.matrix-table tbody th.matrix-leader[data-v-*]` = (0,3,2) beats the
 * global `table th` = (0,0,2); both carry `!important`, so the more specific wins.
 */
.matrix-table tbody th.matrix-leader {
  min-width: 190px;
  background: #ffffff !important;
  border-bottom: 1px solid rgba(226, 232, 240, 0.85) !important;
  color: var(--aa-slate-800, #1e293b) !important;
  font-family: var(--aa-font-sans, 'IBM Plex Sans', sans-serif) !important;
  font-size: 0.9rem !important;
  font-weight: 400 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
}
.matrix-table tbody th.matrix-leader .matrix-species {
  display: block;
  color: var(--aa-slate-600, #475569);
  font-size: 0.86rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
}
.matrix-gene {
  display: block;
  color: var(--aa-slate-800, #1e293b);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: normal;
  text-decoration: none;
  text-transform: none;
}
.matrix-gene:hover { color: var(--aa-teal-700, #0d7377); }
.matrix-locus {
  display: block;
  color: var(--aa-slate-500, #64748b);
  font-family: var(--aa-font-sans);
  font-size: 0.78rem;
  letter-spacing: normal;
  text-transform: none;
}

.matrix-cell { min-width: 135px; }

/*
 * Mini-bars compare values within each metric column.
 */
.matrix-track {
  display: block;
  height: 4px;
  margin-top: 9px;
  border-radius: 2px;
  background: #edf2f5;
  overflow: hidden;
}
.matrix-bar {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #83b4b6;
}
.matrix-value {
  display: block;
  color: var(--aa-slate-800, #1e293b);
  font-family: var(--aa-font-sans);
  font-size: 1rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.matrix-cell.is-missing .matrix-value { color: var(--aa-slate-500, #64748b); font-weight: 400; }

@media (max-width: 960px) {
  .matrix-card { padding: 20px; }
}
</style>
