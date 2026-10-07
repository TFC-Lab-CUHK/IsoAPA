<template>
  <div class="search-page">
    <v-container class="py-10">
      <div class="section-eyebrow mb-2">Search & Filter</div>
      <h1 class="section-heading mb-6">Browse APA Sites</h1>
      <div class="dense-view-note">
        Wide result tables can be scrolled horizontally on small screens. Use landscape mode for easier inspection.
      </div>

      <!-- Glassmorphism Search Frame -->
      <div class="search-frame mb-8">
        <!-- Top bar -->
        <div class="search-frame-topbar">
          <div class="d-flex align-center" style="gap:10px;">
            <div class="topbar-icon">
              <v-icon icon="mdi-filter-variant" size="17" color="white"></v-icon>
            </div>
            <span class="topbar-label">Filter by</span>
          </div>
          <button class="reset-btn" @click="clearFilters">
            <v-icon icon="mdi-refresh" size="14" class="mr-1"></v-icon>
            Reset
          </button>
        </div>

        <!-- Filter inputs -->
        <div class="filter-grid" ref="filterGridRef">
          <div class="filter-card filter-card--select">
            <div class="filter-inner-label" :class="{ 'label-hidden': hasGeneNameValue }">
              <span class="filter-col-icon" style="background: linear-gradient(135deg,#0D7377,#14919B)">
                <v-icon icon="mdi-dna" size="13" color="white"></v-icon>
              </span>
              <span>Gene Name</span>
            </div>
            <v-combobox
              v-model="filters.gene_name"
              v-model:search="geneNameInput"
              :items="geneNameSuggestions"
              item-title="value"
              item-value="value"
              no-filter
              hide-no-data
              clearable
              variant="plain"
              density="compact"
              hide-details
              class="filter-field"
              :menu-props="{ class: 'search-select-menu', width: filterSelectWidth || undefined, offset: 0 }"
              @update:search="onGeneNameSearch"
              @update:model-value="onGeneNameSelect"
            ></v-combobox>
          </div>

          <div class="filter-card filter-card--select">
            <div class="filter-inner-label" :class="{ 'label-hidden': hasTranscriptValue }">
              <span class="filter-col-icon" style="background: linear-gradient(135deg,#355C7D,#4A7898)">
                <v-icon icon="mdi-file-tree-outline" size="13" color="white"></v-icon>
              </span>
              <span>Transcript ID</span>
            </div>
            <v-autocomplete
              v-model="filters.transcript_id"
              :items="transcriptSuggestions"
              item-title="value"
              item-value="value"
              no-filter
              hide-no-data
              clearable
              variant="plain"
              density="compact"
              hide-details
              class="filter-field"
              :menu-props="{ class: 'search-select-menu', width: filterSelectWidth || undefined, offset: 0 }"
              @update:search="onTranscriptSearch"
              @update:model-value="onTranscriptSelect"
            ></v-autocomplete>
          </div>

          <div class="filter-card filter-card--select">
            <div class="filter-inner-label" :class="{ 'label-hidden': !!filters.species }">
              <span class="filter-col-icon" style="background: linear-gradient(135deg,#2F855A,#48A36D)">
                <v-icon icon="mdi-paw" size="13" color="white"></v-icon>
              </span>
              <span>Species</span>
            </div>
            <v-autocomplete
              v-model="filters.species"
              :items="speciesOptions"
              item-title="title"
              item-value="value"
              :custom-filter="filterSpeciesOption"
              clearable
              variant="plain"
              density="compact"
              hide-details
              no-data-text="No matches"
              class="filter-field"
              :menu-props="{ class: 'search-select-menu', width: filterSelectWidth || undefined, offset: 0 }"
              @update:model-value="onSpeciesChange"
            >
              <template #selection="{ item }"><span class="filter-selected-value">{{ item?.raw?.title ?? formatSpeciesName(filters.species) }}</span></template>
              <template #item="{ props, item }">
                <v-list-item v-bind="props" :title="item.raw.title"></v-list-item>
              </template>
            </v-autocomplete>
          </div>

          <div class="filter-card filter-card--select">
            <div class="filter-inner-label" :class="{ 'label-hidden': !!filters.sample }">
              <span class="filter-col-icon" style="background: linear-gradient(135deg,#9A5B13,#C9821A)">
                <v-icon icon="mdi-flask-outline" size="13" color="white"></v-icon>
              </span>
              <span>Sample</span>
            </div>
            <v-autocomplete
              v-model="filters.sample"
              :items="sampleOptions"
              item-title="title"
              item-value="value"
              :custom-filter="filterSubstring"
              clearable
              variant="plain"
              density="compact"
              hide-details
              no-data-text="No matches"
              class="filter-field"
              :menu-props="{ class: 'search-select-menu', width: filterSelectWidth || undefined, offset: 0 }"
              @update:model-value="onSampleChange"
            >
              <template #selection="{ item }"><span class="filter-selected-value">{{ item?.raw?.title ?? formatSampleName(filters.sample) }}</span></template>
              <template #item="{ props, item }">
                <v-list-item v-bind="props" :title="item.raw.title"></v-list-item>
              </template>
            </v-autocomplete>
          </div>
        </div>

        <!-- Actions row -->
        <div class="search-frame-actions">
          <button class="search-btn" @click="submitSearch" :disabled="loading">
            <v-progress-circular v-if="loading" size="16" width="2" indeterminate class="mr-2" color="white"></v-progress-circular>
            <v-icon v-else icon="mdi-magnify" size="18" class="mr-2"></v-icon>
            Search
          </button>
          <v-spacer></v-spacer>
          <button
            class="export-btn"
            @click="exportResults"
            :disabled="results.length === 0"
          >
            <v-icon icon="mdi-download" size="16" class="mr-2"></v-icon>
            Export CSV
          </button>
        </div>
      </div>

      <div class="results-card">
        <v-data-table-server
          :headers="headers"
          :items="results"
          :items-length="totalResults"
          :loading="loading"
          :items-per-page="pageSize"
          :page="page"
          :sort-by="sortBy"
          @update:page="changePage"
          @update:items-per-page="changePageSize"
          @update:sort-by="changeSort"
        >
          <template v-slot:item.gene_name="{ item }">
            <router-link
              :to="{ name: 'GeneDetail', params: { geneId: item.gene_db_id }, query: { species: item.species } }"
              class="text-primary font-weight-medium search-id-link"
              :title="item.gene_name"
            >
              {{ item.gene_name }}
            </router-link>
          </template>

          <template v-slot:item.transcript_id="{ item }">
            <router-link
              :to="{ name: 'LocusDetail', params: { transcriptId: item.transcript_id }, query: { species: item.species } }"
              class="text-primary font-weight-medium text-decoration-underline search-id-link"
              :title="item.transcript_id"
            >
              {{ item.transcript_id }}
            </router-link>
          </template>

          <template v-slot:item.chromosome="{ item }">
            <v-chip size="small" variant="tonal" :title="item.chromosome">{{ item.chromosome }}</v-chip>
          </template>

          <template v-slot:item.strand="{ item }">
            <v-chip size="small" variant="tonal" :title="item.strand">{{ item.strand }}</v-chip>
          </template>

          <template v-slot:item.apa_site_count="{ item }">
            <div class="search-pa-sites-content">
              <v-badge
                :content="item.apa_site_count"
                color="primary"
                inline
              ></v-badge>
            </div>
          </template>

          <template v-slot:item.species="{ item }">
            <v-chip
              size="small"
              :color="getSpeciesColor(item.species)"
              variant="flat"
              :title="formatSpeciesName(item.species)"
            >
              {{ formatSpeciesName(item.species) }}
            </v-chip>
          </template>

          <template v-slot:item.actions="{ item }">
          </template>
        </v-data-table-server>
      </div>

      <v-snackbar v-model="snackbar" :color="snackbarColor">
        {{ snackbarText }}
      </v-snackbar>
    </v-container>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiService } from '@/services/api'
import { formatSampleName, formatSpeciesName } from '@/utils/formatters'

const router = useRouter()
const route = useRoute()

const filterGridRef = ref(null)
const filterSelectWidth = ref(0)

const measureFilterCard = () => {
  const card = filterGridRef.value?.querySelector('.filter-card--select')
  if (card) filterSelectWidth.value = card.offsetWidth
}

const normalizedSampleKey = (name) =>
  formatSampleName(name).toLowerCase()

const normalizedSpeciesKey = (name) =>
  String(name ?? '')
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const speciesTerms = (species) => {
  const entry = species && typeof species === 'object'
    ? species
    : { value: species, title: species, aliases: [] }
  return [entry.value, entry.title, ...(entry.aliases || [])]
    .map(normalizedSpeciesKey)
    .filter(Boolean)
}

const speciesMatchRank = (species, query) => {
  const normalizedQuery = normalizedSpeciesKey(query)
  if (!normalizedQuery) return 0
  const terms = speciesTerms(species)
  if (terms.includes(normalizedQuery)) return 0
  if (terms.some(term => term.startsWith(normalizedQuery))) return 1
  if (terms.some(term => term.includes(normalizedQuery))) return 2
  return Number.POSITIVE_INFINITY
}

const loading = ref(false)
const results = ref([])
const page = ref(1)
const pageSize = ref(20)
const totalResults = ref(0)
const sortBy = ref([])
const DEFAULT_SPECIES = 'Human'

const filters = reactive({
  gene_name: '',
  transcript_id: '',
  species: '',
  sample: ''
})

const geneNameInput = ref('')
const transcriptInput = ref('')
const hasGeneNameValue = computed(() => !!String(geneNameInput.value || filters.gene_name || '').trim())
const hasTranscriptValue = computed(() => !!String(transcriptInput.value || filters.transcript_id || '').trim())

const speciesList = ref([{ title: 'Mus musculus', value: 'Mouse' }])
const sampleList = ref([
  { title: 'A549', value: 'A549', normalizedValue: normalizedSampleKey('A549'), species: 'Human' },
  { title: 'HepG2', value: 'HepG2', normalizedValue: normalizedSampleKey('HepG2'), species: 'Human' },
  { title: 'K562', value: 'K562', normalizedValue: normalizedSampleKey('K562'), species: 'Human' }
])
const sampleOptions = computed(() =>
  sampleList.value
    .filter(sample => !filters.species || sample.species === filters.species)
    .filter((sample, index, list) => (
      filters.species || list.findIndex(item => item.normalizedValue === sample.normalizedValue) === index
    ))
    .map(sample => ({
      title: sample.title ?? formatSampleName(sample.value ?? sample),
      value: sample.value ?? sample
    }))
)
const speciesOptions = computed(() =>
  speciesList.value
    .filter(species => {
      if (!filters.sample) return true
      return sampleList.value.some(sample =>
        sample.value === filters.sample && sample.species === species.value
      )
    })
    .map(species => ({
      title: species.title ?? formatSpeciesName(species.value ?? species),
      value: species.value ?? species,
      aliases: species.aliases || []
    }))
)

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

let searchTimeout = null

const headers = [
  {
    title: 'Gene Name',
    key: 'gene_name',
    sortable: true,
    nowrap: true,
    width: 'calc((100% - 270px) / 4)',
    cellProps: { class: 'search-cell-nowrap' },
    headerProps: { class: 'search-cell-nowrap' },
  },
  {
    title: 'Transcript ID',
    key: 'transcript_id',
    sortable: true,
    nowrap: true,
    width: 'calc((100% - 270px) / 4)',
    cellProps: { class: 'search-cell-nowrap' },
    headerProps: { class: 'search-cell-nowrap' },
  },
  {
    title: 'Chromosome',
    key: 'chromosome',
    sortable: true,
    nowrap: true,
    width: 'calc((100% - 270px) / 4)',
    align: 'center',
    cellProps: { class: 'search-cell-nowrap' },
    headerProps: { class: 'search-cell-nowrap' },
  },
  {
    title: 'Strand',
    key: 'strand',
    sortable: true,
    nowrap: true,
    width: 120,
    align: 'center',
    cellProps: { class: 'search-cell-nowrap search-cell-strand' },
    headerProps: { class: 'search-cell-nowrap search-cell-strand' },
  },
  {
    title: 'No. PA Sites',
    key: 'apa_site_count',
    sortable: true,
    width: 150,
    nowrap: true,
    align: 'center',
    cellProps: { class: 'search-cell-nowrap search-cell-pa-sites' },
    headerProps: { class: 'search-cell-nowrap search-cell-pa-sites' },
  },
  {
    title: 'Species',
    key: 'species',
    sortable: true,
    width: 'calc((100% - 270px) / 4)',
    nowrap: true,
    cellProps: { class: 'search-cell-nowrap' },
    headerProps: { class: 'search-cell-nowrap' },
  },
]

const speciesColors = {
  'Human': '#B63F5A',
  'Mouse': '#0D7377',
  'Rat': '#2F855A',
  'Zebrafish': '#355C7D'
}

const speciesColorPalette = [
  '#0D7377',
  '#355C7D',
  '#8A5A44',
  '#7A4E92',
  '#B7791F',
  '#2F855A',
  '#9A5B13',
  '#4C5F91',
  '#0F766E',
  '#A43F5C',
  '#64748B',
  '#8F5E67',
]

const getSpeciesColor = (species) => {
  if (speciesColors[species]) {
    return speciesColors[species]
  }

  const key = String(species || '')
  let hash = 0

  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0
  }

  return speciesColorPalette[hash % speciesColorPalette.length]
}

const filterSubstring = (value, query) =>
  String(value?.value ?? value ?? '').toLowerCase().includes(query.toLowerCase()) ||
  String(value?.title ?? value?.display_name ?? formatSampleName(value)).toLowerCase().includes(query.toLowerCase())

const filterSpeciesOption = (value, query, item) => {
  const species = item?.raw || item || value
  return Number.isFinite(speciesMatchRank(species, query))
}

const resolveSpeciesValue = (value) => {
  const query = normalizedSpeciesKey(value)
  if (!query) return ''

  const matches = speciesList.value
    .map(species => ({ species, rank: speciesMatchRank(species, query) }))
    .filter(match => Number.isFinite(match.rank))
    .sort((a, b) => a.rank - b.rank || a.species.title.localeCompare(b.species.title))

  if (!matches.length) return String(value)
  const bestMatches = matches.filter(match => match.rank === matches[0].rank)
  return bestMatches.length === 1 ? bestMatches[0].species.value : String(value)
}

const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    search()
  }, 500)
}

const onSpeciesChange = () => {
  if (filters.sample && !sampleOptions.value.some(sample => sample.value === filters.sample)) {
    filters.sample = ''
  }
  page.value = 1
  debouncedSearch()
}

const onSampleChange = () => {
  if (filters.species && !speciesOptions.value.some(species => species.value === filters.species)) {
    filters.species = ''
  }
  page.value = 1
  debouncedSearch()
}

const commitTextFilters = () => {
  filters.gene_name = geneNameInput.value.trim()
  filters.transcript_id = transcriptInput.value.trim()
}

const search = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      limit: pageSize.value
    }
    if (sortBy.value.length) {
      params.sort_by = sortBy.value[0].key
      params.sort_desc = sortBy.value[0].order === 'desc'
    }

    if (filters.gene_name) params.gene_name = filters.gene_name
    if (filters.transcript_id) params.transcript_id = filters.transcript_id
    if (filters.species) params.species = filters.species
    if (filters.sample) params.sample = filters.sample

    const data = await apiService.search(params)
    results.value = data.items
    totalResults.value = data.total
  } catch (error) {
    console.error('Search failed:', error)
    snackbarText.value = 'Search failed. Please try again.'
    snackbarColor.value = 'error'
    snackbar.value = true
  } finally {
    loading.value = false
  }
}

const submitSearch = () => {
  commitTextFilters()
  page.value = 1
  search()
}

const clearFilters = () => {
  filters.gene_name = ''
  filters.transcript_id = ''
  geneNameInput.value = ''
  transcriptInput.value = ''
  filters.species = ''
  filters.sample = ''
  page.value = 1
  search()
}

const changePage = (newPage) => {
  page.value = newPage
  search()
}

const changePageSize = (newSize) => {
  pageSize.value = newSize
  page.value = 1
  search()
}

const changeSort = (newSort) => {
  sortBy.value = newSort
  page.value = 1
  search()
}

const exportResults = () => {
  const headers = ['Gene Name', 'Transcript ID', 'Gene ID', 'Chromosome', 'Strand', 'APA Site Count', 'Species', 'Tissues']
  const rows = results.value.map(item => [
    item.gene_name,
    item.transcript_id,
    item.gene_id,
    item.chromosome,
    item.strand,
    item.apa_site_count,
    formatSpeciesName(item.species),
    item.cell_lines.map(formatSampleName).join('; ')
  ])

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `apa_sites_export_${Date.now()}.csv`
  a.click()
  window.URL.revokeObjectURL(url)

  snackbarText.value = 'Export completed successfully!'
  snackbarColor.value = 'success'
  snackbar.value = true
}

onMounted(async () => {
  try {
    const [speciesData, samplesData] = await Promise.all([
      apiService.getSpecies(),
      apiService.getSamples()
    ])

    if (speciesData && speciesData.length > 0) {
      speciesList.value = speciesData.map(s => ({
        title: s.display_name ?? formatSpeciesName(s),
        value: s.name,
        aliases: Array.isArray(s.aliases) ? s.aliases : []
      }))
    }
    if (samplesData && samplesData.length > 0) {
      const seen = new Set()
      sampleList.value = samplesData
        .filter(s => {
          const key = `${normalizedSampleKey(s.name)}::${s.species || ''}`
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
        .map(s => ({
          title: formatSampleName(s.display_name ?? s.name),
          value: s.name,
          normalizedValue: normalizedSampleKey(s.name),
          species: s.species
        }))
    }
  } catch (error) {
    console.error('Failed to load filters:', error)
  }

  const hasRouteFilters = Object.keys(route.query || {}).length > 0
  if (route.query) {
    if (route.query.gene_name) {
      filters.gene_name = route.query.gene_name
      geneNameInput.value = route.query.gene_name
    }
    if (route.query.transcript_id) {
      filters.transcript_id = route.query.transcript_id
      transcriptInput.value = route.query.transcript_id
    }
    if (route.query.sample) filters.sample = route.query.sample
    if (route.query.species) filters.species = resolveSpeciesValue(route.query.species)
  }
  if (!hasRouteFilters && speciesList.value.some(species => species.value === DEFAULT_SPECIES)) {
    filters.species = DEFAULT_SPECIES
  }

  search()
  measureFilterCard()
  window.addEventListener('resize', measureFilterCard)
})

onUnmounted(() => {
  window.removeEventListener('resize', measureFilterCard)
})

watch(() => route.query, (newQuery) => {
  filters.gene_name = ''
  filters.transcript_id = ''
  filters.sample = ''
  filters.species = ''
  geneNameInput.value = ''
  transcriptInput.value = ''

  if (newQuery.gene_name) {
    filters.gene_name = newQuery.gene_name
    geneNameInput.value = newQuery.gene_name
  }
  if (newQuery.transcript_id) {
    filters.transcript_id = newQuery.transcript_id
    transcriptInput.value = newQuery.transcript_id
  }
  if (newQuery.sample) filters.sample = newQuery.sample
  if (newQuery.species) filters.species = resolveSpeciesValue(newQuery.species)
  if (Object.keys(newQuery || {}).length === 0 && speciesList.value.some(species => species.value === DEFAULT_SPECIES)) {
    filters.species = DEFAULT_SPECIES
  }
  search()
})

const geneNameSuggestions = ref([])
const transcriptSuggestions = ref([])
let geneNameTimer = null
let transcriptTimer = null

const onGeneNameSearch = (val) => {
  geneNameInput.value = val ?? ''
  clearTimeout(geneNameTimer)
  if (!val) { geneNameSuggestions.value = []; return }
  geneNameTimer = setTimeout(async () => {
    try {
      geneNameSuggestions.value = await apiService.autocomplete(val, 'gene_name', 50)
    } catch {
      geneNameSuggestions.value = []
    }
  }, 250)
}

const onTranscriptSearch = (val) => {
  transcriptInput.value = val ?? ''
  clearTimeout(transcriptTimer)
  if (!val) { transcriptSuggestions.value = []; return }
  transcriptTimer = setTimeout(async () => {
    try {
      transcriptSuggestions.value = await apiService.autocomplete(val, 'transcript_id', 50)
    } catch {
      transcriptSuggestions.value = []
    }
  }, 250)
}

const onGeneNameSelect = (val) => {
  geneNameInput.value = typeof val === 'object' ? (val?.value ?? '') : (val ?? '')
  filters.gene_name = geneNameInput.value.trim()
  page.value = 1
  if (filters.gene_name) search()
}

const onTranscriptSelect = (val) => {
  transcriptInput.value = val ?? ''
  filters.transcript_id = transcriptInput.value.trim()
  page.value = 1
  if (filters.transcript_id) search()
}
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 8% 4%, rgba(13, 115, 119, 0.10), transparent 30%),
    radial-gradient(circle at 90% 0%, rgba(53, 92, 125, 0.10), transparent 28%),
    rgb(var(--v-theme-background));
}

/* ── Eyebrow + Heading ──────────────────────────────────────── */
.section-eyebrow {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #14919B;
  background: rgba(20, 145, 155, 0.08);
  border-radius: 20px;
  padding: 3px 12px;
}
.section-heading {
  font-size: clamp(2rem, 3vw, 2.65rem);
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--aa-slate-800);
}

/* ── Search Frame ───────────────────────────────────────────── */
.search-frame {
  border-radius: 22px;
  overflow: hidden;
}

.search-frame-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: linear-gradient(90deg, rgba(13, 115, 119, 0.07) 0%, rgba(20, 145, 155, 0.02) 100%);
  border-bottom: 1px solid rgba(13, 115, 119, 0.10);
}

.topbar-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0D7377, #14919B);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.topbar-label {
  font-family: var(--aa-font-display);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--aa-slate-600);
}

.reset-btn {
  display: flex;
  align-items: center;
  font-size: 0.80rem;
  font-weight: 500;
  color: #0D7377;
  background: none;
  border: none;
  cursor: pointer;
  padding: 5px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}
.reset-btn:hover {
  background: rgba(13, 115, 119, 0.08);
}

/* ── Filter Grid ─────────────────────────────────────────────── */
.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 20px 24px 8px;
}
@media (max-width: 960px) {
  .filter-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .filter-grid {
    grid-template-columns: 1fr;
    gap: 10px;
    padding: 14px 14px 8px;
  }
}

.filter-card {
  position: relative;
  background: #ffffff;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 1px solid rgba(203, 213, 225, 0.56);
  border-radius: 12px;
  padding: 0;
  height: 50px;
  display: flex;
  align-items: center;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(13, 115, 119, 0.07), inset 0 1px 0 rgba(255, 255, 255, 0.62);
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s, border-radius 0.15s;
}
.filter-card:hover {
  background: #ffffff;
  border-color: rgba(20, 145, 155, 0.22);
  box-shadow: 0 8px 24px rgba(13, 115, 119, 0.11), 0 2px 6px rgba(13, 115, 119, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.54);
}
.filter-card:focus-within {
  background: #ffffff;
  border-color: rgba(20, 145, 155, 0.46);
  box-shadow: 0 0 0 3px rgba(20, 145, 155, 0.13), 0 8px 28px rgba(13, 115, 119, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.54);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
/* Flat-bottom only when Vuetify menu is actually open — not on mere focus */
.filter-card--select:has([aria-expanded="true"]) {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  border-bottom-color: rgba(20, 145, 155, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.54);
}

/* Label floats over the input area; fades on hover, focus, or when value is filled */
.filter-inner-label {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--aa-font-display);
  font-size: 0.70rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--aa-slate-500);
  white-space: nowrap;
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.filter-inner-label.label-hidden,
.filter-card:hover .filter-inner-label,
.filter-card:focus-within .filter-inner-label {
  opacity: 0;
  transform: translateY(-50%) translateX(-4px);
}

.filter-col-icon {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* v-field spans full card width (no card padding) → dropdown width = card width */
.filter-field {
  flex: 1;
  min-width: 0;
  align-self: stretch;
}
.filter-field :deep(.v-field__input) {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  padding-left: 0 !important;
  font-size: 0.92rem;
  font-weight: 500;
  color: var(--aa-slate-800);
  min-height: unset !important;
}
.filter-field :deep(.v-field) {
  padding: 0 12px !important;
  align-items: center;
  height: 100%;
}
.filter-field :deep(.v-input__control) {
  min-height: unset !important;
  height: 100%;
}
.filter-field :deep(.v-field__clearable) {
  padding-top: 0 !important;
  padding-right: 0 !important;
}
.filter-field :deep(.v-select__selection),
.filter-field :deep(.v-autocomplete__selection) {
  margin: 0 !important;
  min-width: 0;
}
.filter-field :deep(.v-select__selection-text),
.filter-field :deep(.v-autocomplete__selection-text),
.filter-selected-value {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.91rem;
  font-weight: 500;
  line-height: 1.25;
}

/* ── Actions row ────────────────────────────────────────────── */
.search-frame-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px 20px;
  border-top: 1px solid rgba(13, 115, 119, 0.08);
}

.search-btn {
  display: inline-flex;
  align-items: center;
  height: 42px;
  padding: 0 24px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #0D7377, #14919B);
  color: white;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(13, 115, 119, 0.24);
  transition: box-shadow 0.2s, opacity 0.15s, transform 0.15s;
}
.search-btn:hover:not(:disabled) {
  box-shadow: 0 14px 30px rgba(13, 115, 119, 0.32);
  transform: translateY(-1px);
}
.search-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  height: 42px;
  padding: 0 20px;
  border-radius: 10px;
  border: 1.5px solid rgba(13, 115, 119, 0.40);
  background: rgba(255, 255, 255, 0.58);
  color: #0D7377;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.export-btn:hover:not(:disabled) {
  background: rgba(13, 115, 119, 0.06);
  border-color: #0D7377;
}
.export-btn:disabled {
  opacity: 0.40;
  cursor: not-allowed;
}

/* ── Results Card — glassmorphism ───────────────────────────── */
.results-card {
  border-radius: 22px;
  overflow: hidden;
}

/* ── Data table ─────────────────────────────────────────────── */
.search-page :deep(.v-data-table) {
  background: transparent !important;
}

.search-page :deep(.v-table__wrapper) {
  overflow-x: auto;
}

.search-page :deep(.v-table__wrapper > table) {
  min-width: 760px;
  table-layout: fixed;
}

.search-page :deep(.v-data-table__th) {
  background: #f1f8f8 !important;
  font-family: var(--aa-font-display) !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  padding-left: 28px !important;
  padding-right: 14px !important;
  letter-spacing: 0.09em;
  color: var(--aa-slate-600) !important;
  border-bottom: 1px solid rgba(13, 115, 119, 0.10) !important;
  white-space: nowrap;
}
.search-page :deep(.v-data-table__td) {
  padding: 10px 14px 10px 28px !important;
  background: transparent !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05) !important;
  font-size: 14px;
  line-height: 1.45;
  color: var(--aa-slate-700);
}

.search-page :deep(.search-cell-nowrap) {
  white-space: nowrap !important;
  overflow: hidden;
  text-overflow: ellipsis;
  width: calc((100% - 270px) / 4);
}

.search-page :deep(.search-cell-strand) {
  width: 120px;
  padding-left: 14px !important;
  padding-right: 10px !important;
}

.search-page :deep(.search-cell-pa-sites) {
  width: 150px;
  padding-left: 14px !important;
  padding-right: 10px !important;
}

.search-pa-sites-content {
  display: flex;
  justify-content: center;
  width: 100%;
}

.search-id-link {
  display: inline-block;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.search-page :deep(.search-cell-nowrap .v-chip) {
  max-width: 100%;
}

.search-page :deep(.search-cell-nowrap .v-chip__content) {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-page :deep(.v-data-table__tr:hover .v-data-table__td) {
  background: rgba(13, 115, 119, 0.03) !important;
}
/* ── Data table footer — Glassmorphism ──────────────────────── */
.search-page :deep(.v-data-table-footer) {
  border-top: 1px solid rgba(13, 115, 119, 0.10) !important;
  background: rgba(13, 115, 119, 0.03) !important;
  padding: 8px 20px !important;
  font-family: var(--aa-font-sans);
}

/* "Items per page:" label */
.search-page :deep(.v-data-table-footer__items-per-page span) {
  font-size: 13px !important;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.45);
  white-space: nowrap;
}

/* Items per page select */
.search-page :deep(.v-data-table-footer__items-per-page .v-field) {
  background: rgba(255, 255, 255, 0.70) !important;
  border-radius: 8px !important;
  border: 1px solid rgba(13, 115, 119, 0.20) !important;
  box-shadow: none !important;
  min-height: 34px !important;
}
.search-page :deep(.v-data-table-footer__items-per-page .v-field__input) {
  font-size: 13px !important;
  font-family: var(--aa-font-sans);
  color: rgba(0, 0, 0, 0.72) !important;
  min-height: 34px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
.search-page :deep(.v-data-table-footer__items-per-page .v-field__append-inner .v-icon) {
  font-size: 16px !important;
  color: rgba(13, 115, 119, 0.50) !important;
}

/* "X–Y of Z" info text */
.search-page :deep(.v-data-table-footer__info) {
  font-size: 13px !important;
  font-weight: 500;
  font-family: var(--aa-font-sans);
  color: rgba(0, 0, 0, 0.45);
}

/* Pagination buttons — color only, no structural overrides */
.search-page :deep(.v-data-table-footer__pagination .v-btn) {
  color: rgba(13, 115, 119, 0.65) !important;
}
.search-page :deep(.v-data-table-footer__pagination .v-btn:not(.v-btn--disabled):hover) {
  color: #0D7377 !important;
}
.search-page :deep(.v-data-table-footer__pagination .v-btn.v-btn--disabled) {
  color: rgba(0, 0, 0, 0.22) !important;
}

/* ── Chips in table ─────────────────────────────────────────── */
.search-page :deep(.v-chip) {
  font-size: 13px;
  font-weight: 500;
}

@media (max-width: 640px) {
  .search-page :deep(.v-container) {
    padding-top: 26px !important;
    padding-bottom: 34px !important;
  }

  .search-frame {
    margin-bottom: 20px !important;
  }

  .search-frame-topbar {
    padding: 12px 14px;
  }

  .search-frame-actions {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
    padding: 12px 14px 14px;
  }

  .search-frame-actions .v-spacer {
    display: none;
  }

  .search-btn,
  .export-btn {
    justify-content: center;
    width: 100%;
  }

  .search-page :deep(.v-table__wrapper > table) {
    min-width: 820px;
  }

  .search-page :deep(.v-data-table__th) {
    padding-left: 18px !important;
    padding-right: 12px !important;
  }

  .search-page :deep(.v-data-table__td) {
    padding: 9px 12px 9px 18px !important;
  }

  .search-page :deep(.v-data-table-footer) {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
    padding: 10px 14px !important;
  }
}
</style>

<!-- Global: Vuetify overlays are teleported outside the component root;
     scoped styles cannot reach them — this block is intentionally unscoped. -->
<style>
.search-select-menu .v-overlay__content {
  min-width: unset !important;
  max-width: unset !important;
  border-radius: 0 0 12px 12px !important;
  overflow: hidden !important;
}
.search-select-menu .v-list {
  background: #ffffff !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid rgba(20, 145, 155, 0.28) !important;
  border-top: 1px solid rgba(20, 145, 155, 0.12) !important;
  border-radius: 0 0 12px 12px !important;
  box-shadow: 0 16px 40px rgba(13, 115, 119, 0.14), 0 6px 16px rgba(13, 115, 119, 0.08) !important;
  padding: 6px !important;
}
.search-select-menu .v-list-item {
  border-radius: 8px !important;
  min-height: 36px !important;
  margin: 1px 0 !important;
  padding: 0 12px !important;
  transition: background 0.15s !important;
}
.search-select-menu .v-list-item:hover {
  background: rgba(13, 115, 119, 0.08) !important;
}
.search-select-menu .v-list-item--active {
  background: rgba(13, 115, 119, 0.12) !important;
}
.search-select-menu .v-list-item-title {
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  color: rgba(0, 0, 0, 0.75) !important;
  letter-spacing: 0.01em !important;
}
.search-select-menu .v-list-item--active .v-list-item-title {
  color: #0D7377 !important;
  font-weight: 600 !important;
}
</style>
