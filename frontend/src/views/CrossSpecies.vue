<template>
  <div class="compare-page">
    <section class="hero-section">
      <div class="hero-bg"></div>
      <v-container class="hero-content">
        <h1 class="text-h3 text-white mb-3">Cross-species Comparison</h1>
        <p class="text-h6 text-white opacity-90">
          Compare transcript-linked PA-site architecture and usage across orthologous genes.
        </p>
      </v-container>
    </section>

    <v-container class="compare-content">
      <section class="search-frame">
        <div class="search-frame-topbar">
          <div class="topbar-left">
            <span class="topbar-icon"><v-icon icon="mdi-vector-link" size="16" color="white"></v-icon></span>
            <span class="topbar-label">Find orthologs</span>
          </div>
          <span class="topbar-source">NCBI Gene orthologs</span>
        </div>

        <div class="query-grid">
          <v-autocomplete
            v-model="selectedSpecies"
            :items="speciesOptions"
            item-title="title"
            item-value="value"
            label="Source species"
            variant="outlined"
            density="comfortable"
            hide-details
            class="compare-field"
          ></v-autocomplete>

          <v-autocomplete
            v-model="selectedSourceOption"
            :items="geneSuggestions"
            item-title="title"
            return-object
            no-filter
            clearable
            hide-no-data
            label="Gene symbol or GeneID"
            variant="outlined"
            density="comfortable"
            hide-details
            class="compare-field"
            v-model:search="geneQuery"
            @update:search="onGeneQuery"
            @keyup.enter="submitSourceSearch"
          >
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps" :title="item.raw.gene_name">
                <template #subtitle>
                  GeneID {{ item.raw.gene_id }} · {{ item.raw.ortholog_species_count }} species
                </template>
              </v-list-item>
            </template>
          </v-autocomplete>

          <button class="primary-action" :disabled="sourceLoading" @click="submitSourceSearch">
            <v-progress-circular v-if="sourceLoading" indeterminate size="17" width="2" color="white" />
            <v-icon v-else icon="mdi-compare-horizontal" size="19"></v-icon>
            Compare orthologs
          </button>
        </div>

        <div v-if="!orthologSet" class="example-row">
          <span>Try</span>
          <button
            v-for="example in EXAMPLE_GENES"
            :key="example"
            class="example-chip"
            type="button"
            @click="runExample(example)"
          >
            {{ example }}
          </button>
        </div>

        <v-alert v-if="sourceError" type="error" variant="tonal" density="compact" class="mt-4">
          {{ sourceError }}
        </v-alert>
      </section>

      <div v-if="orthologLoading" class="skeleton-stack">
        <div class="skeleton-block skeleton-block--picker"></div>
        <div class="skeleton-block skeleton-block--matrix"></div>
      </div>

      <section v-else-if="!orthologSet" class="section-card intro-card">
        <div class="section-eyebrow">How it works</div>
        <h2>From orthologs to PAS usage</h2>
        <p class="intro-lead">
          Select a gene to explore PAS profiles across species, then inspect usage within each transcript.
        </p>
        <ol class="intro-steps">
          <li>
            <span class="intro-step-index">1</span>
            <strong>Pick a source gene</strong>
            <span>Search by gene symbol or GeneID.</span>
          </li>
          <li>
            <span class="intro-step-index">2</span>
            <strong>Choose the species</strong>
            <span>Compare up to eight genes linked by NCBI Gene orthology.</span>
          </li>
          <li>
            <span class="intro-step-index">3</span>
            <strong>Explore PAS usage</strong>
            <span>
              Switch between pooled gene profiles and individual transcripts.
            </span>
          </li>
        </ol>
      </section>

      <template v-else>
        <OrthologSpeciesPicker
          :ortholog-set="orthologSet"
          :selected-ids="selectedGeneIds"
          :max-selection="MAX_COMPARISON_GENES"
          @update:selected-ids="onSelectionChange"
        />

        <div
          v-if="comparisonLoading"
          class="skeleton-stack"
          :style="reservedHeight ? { minHeight: `${reservedHeight}px` } : null"
        >
          <div class="skeleton-block skeleton-block--matrix"></div>
          <div class="skeleton-block skeleton-block--tracks"></div>
        </div>

        <div v-else-if="activeComparison" ref="comparisonStack" class="comparison-stack">
          <ComparisonMatrix :genes="activeComparison.genes" />
          <PasArchitecturePanel
            :genes="activeComparison.genes"
            :sample-options="sampleOptions"
            :sample-key="selectedSample"
            :view-mode="viewMode"
            :scale="axisScale"
            @update:sample-key="onSampleChange"
            @update:view-mode="onViewModeChange"
            @update:scale="onScaleChange"
          />
        </div>

        <section
          v-else
          class="section-card state-card"
          :class="{ 'state-card--error': comparisonPlaceholder.tone === 'error' }"
        >
          <span class="state-icon">
            <v-icon :icon="comparisonPlaceholder.icon" size="22"></v-icon>
          </span>
          <h3>{{ comparisonPlaceholder.title }}</h3>
          <p>{{ comparisonPlaceholder.body }}</p>
          <button
            v-if="comparisonPlaceholder.retry"
            class="state-action"
            type="button"
            :disabled="!selectedGeneIds.length"
            @click="loadComparison"
          >
            <v-icon icon="mdi-refresh" size="17"></v-icon>
            Reload comparison
          </button>
        </section>
      </template>
    </v-container>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiService } from '@/services/api'
import ComparisonMatrix from '@/components/crossspecies/ComparisonMatrix.vue'
import OrthologSpeciesPicker from '@/components/crossspecies/OrthologSpeciesPicker.vue'
import PasArchitecturePanel from '@/components/crossspecies/PasArchitecturePanel.vue'
import { AXIS_SCALE_LINEAR, AXIS_SCALE_LOG } from '@/utils/pasLayout'

const MAX_COMPARISON_GENES = 8
const DEFAULT_SELECTION_SIZE = 4
const SPECIES_PRIORITY = ['Human', 'Mouse', 'Rattus_norvegicus', 'Danio_rerio']
const EXAMPLE_GENES = ['PEX11A', 'CPSF6', 'NUDT21', 'TP53']
const GENE_SEARCH_DEBOUNCE_MS = 220

const route = useRoute()
const router = useRouter()

const speciesOptions = ref([])
const selectedSpecies = ref('Human')
const geneQuery = ref('')
const geneSuggestions = ref([])
const selectedSourceOption = ref(null)
const sourceLoading = ref(false)
/** Gene lookup / ortholog retrieval failures — rendered inside the search frame. */
const sourceError = ref('')
const orthologLoading = ref(false)
const orthologSet = ref(null)
const selectedGeneIds = ref([])
const comparisonLoading = ref(false)
const comparisonData = ref(null)
/** Comparison payload failures — rendered where the comparison would have been. */
const comparisonError = ref('')
const selectedSample = ref('')
const viewMode = ref('gene')
const axisScale = ref(AXIS_SCALE_LINEAR)

const comparisonStack = ref(null)
/*
 * Height of the comparison currently on screen, captured just before it is
 * swapped for the loading skeleton. The skeleton is a fixed ~700px while a real
 * comparison runs far taller, so without this the document collapses mid-reload,
 * the browser clamps the scroll position to the shorter page, and toggling a
 * species throws the reader back to the top of the page.
 */
const reservedHeight = ref(0)

const reserveComparisonHeight = () => {
  reservedHeight.value = comparisonStack.value?.offsetHeight || 0
}

let geneSearchTimer = null
let orthologRequest = 0
let comparisonRequest = 0

const sourceGeneId = computed(() => orthologSet.value?.source_gene?.gene_db_id ?? null)

/** Stable identity of a gene-id selection, used to tag and validate comparison payloads. */
const selectionKey = ids => [...ids].sort((a, b) => a - b).join(',')

/** Only expose a payload that was computed for the selection currently on screen. */
const activeComparison = computed(() =>
  comparisonData.value && comparisonData.value.forKey === selectionKey(selectedGeneIds.value)
    ? comparisonData.value
    : null
)

const sampleOptions = computed(() => [
  { title: 'Mean across supporting groups', value: '' },
  ...(activeComparison.value?.sample_options || []).map(sample => ({
    value: sample.value,
    title: `${sample.title} · ${sample.species_count} species`
  }))
])

const comparisonPlaceholder = computed(() => {
  if (comparisonError.value) {
    return {
      tone: 'error',
      icon: 'mdi-alert-circle-outline',
      title: 'Comparison unavailable',
      body: comparisonError.value,
      retry: true
    }
  }
  if (!orthologSet.value?.orthologs?.length) {
    return {
      tone: 'empty',
      icon: 'mdi-vector-link',
      title: 'No ortholog partners found',
      body: 'NCBI Gene lists no direct ortholog for this gene among the species covered by IsoAPA.',
      retry: false
    }
  }
  if (!selectedGeneIds.value.length) {
    return {
      tone: 'empty',
      icon: 'mdi-cursor-default-click-outline',
      title: 'Select at least one species',
      body: 'Choose ortholog cards above to place their PA-site architectures on a shared axis.',
      retry: false
    }
  }
  return {
    tone: 'empty',
    icon: 'mdi-compare-horizontal',
    title: 'Comparison not loaded yet',
    body: 'The selection changed before a comparison finished. Reload it to continue.',
    retry: true
  }
})

/*
 * `v-model:search` owns writing geneQuery, which lets runExample() push a symbol into the
 * input programmatically. This handler therefore only schedules the lookup, and reads the
 * emitted value rather than geneQuery so it does not depend on listener ordering.
 */
const onGeneQuery = value => {
  const term = (value || '').trim()
  clearTimeout(geneSearchTimer)
  if (!selectedSpecies.value || term.length < 2) {
    geneSuggestions.value = []
    return
  }
  geneSearchTimer = setTimeout(async () => {
    try {
      const rows = await apiService.searchOrthologGenes(selectedSpecies.value, term)
      geneSuggestions.value = rows.map(row => ({ ...row, title: `${row.gene_name} · ${row.gene_id}` }))
    } catch {
      geneSuggestions.value = []
    }
  }, GENE_SEARCH_DEBOUNCE_MS)
}

/**
 * A single-token query names one gene (symbol or GeneID), so a near-miss must never be
 * substituted for it — searching TP53 may not silently load TP53BP1. Only free-text
 * queries fall back to the best-ranked hit.
 */
const isExactGeneLookup = query => !/\s/.test(query)

const resolveSourceGene = async query => {
  const results = await apiService.searchOrthologGenes(selectedSpecies.value, query, 20)
  const exact = results.find(
    row => row.gene_name.toLowerCase() === query.toLowerCase() || String(row.gene_id) === query
  )
  if (exact) return exact
  if (!isExactGeneLookup(query)) return results[0]
  const nearby = results
    .slice(0, 3)
    .map(row => row.gene_name)
    .join(', ')
  throw new Error(
    `No exact match for "${query}" among ortholog-mapped genes in this species.` +
      (nearby ? ` Similar symbols: ${nearby}.` : '')
  )
}

const submitSourceSearch = async () => {
  sourceError.value = ''
  sourceLoading.value = true
  try {
    let source = selectedSourceOption.value
    if (!source?.gene_db_id) {
      const query = geneQuery.value.trim()
      if (!query) throw new Error('Enter a gene symbol or GeneID.')
      source = await resolveSourceGene(query)
    }
    if (!source?.gene_db_id) throw new Error('No ortholog-mapped gene matched this query.')
    await loadOrthologSet(source.gene_db_id)
  } catch (error) {
    sourceError.value = error?.response?.data?.detail || error?.message || 'Unable to find orthologs for this gene.'
  } finally {
    sourceLoading.value = false
  }
}

const runExample = async symbol => {
  selectedSourceOption.value = null
  geneQuery.value = symbol
  await submitSourceSearch()
}

const defaultSelection = data => {
  const selected = [data.source_gene.gene_db_id]
  const seenSpecies = new Set([data.source_gene.species])
  const ranked = [...data.orthologs].sort((a, b) => {
    const rankA = SPECIES_PRIORITY.indexOf(a.species)
    const rankB = SPECIES_PRIORITY.indexOf(b.species)
    return (
      (rankA === -1 ? 99 : rankA) - (rankB === -1 ? 99 : rankB) ||
      a.scientific_name.localeCompare(b.scientific_name)
    )
  })
  for (const gene of ranked) {
    if (selected.length >= DEFAULT_SELECTION_SIZE) break
    if (seenSpecies.has(gene.species)) continue
    selected.push(gene.gene_db_id)
    seenSpecies.add(gene.species)
  }
  return selected
}

/** Keep the source gene first: the API validates orthology against gene_ids[0]. */
const withSourceFirst = ids => {
  const sourceId = sourceGeneId.value
  return [...new Set([sourceId, ...ids.filter(id => id !== sourceId)])]
    .filter(Boolean)
    .slice(0, MAX_COMPARISON_GENES)
}

const restoreSelection = data => {
  const requested = String(route.query.genes || '')
    .split(',')
    .map(value => Number(value.trim()))
    .filter(value => Number.isInteger(value) && value > 0)
  const available = new Set([
    data.source_gene.gene_db_id,
    ...data.orthologs.map(gene => gene.gene_db_id)
  ])
  const valid = requested.filter(id => available.has(id))
  return valid.length ? valid : defaultSelection(data)
}

const loadOrthologSet = async (geneDbId, { restoreFromUrl = false } = {}) => {
  const requestId = ++orthologRequest
  // Invalidate any in-flight comparison so the previous gene's tracks cannot survive here.
  comparisonRequest += 1
  comparisonData.value = null
  comparisonError.value = ''
  comparisonLoading.value = true
  sourceError.value = ''
  orthologLoading.value = true
  try {
    const data = await apiService.getGeneOrthologs(geneDbId)
    if (requestId !== orthologRequest) return
    orthologSet.value = data
    selectedSpecies.value = data.source_gene.species
    selectedSourceOption.value = {
      ...data.source_gene,
      title: `${data.source_gene.gene_name} · ${data.source_gene.gene_id}`
    }
    geneQuery.value = data.source_gene.gene_name
    selectedGeneIds.value = withSourceFirst(
      restoreFromUrl ? restoreSelection(data) : defaultSelection(data)
    )
    await syncUrl()
    await loadComparison()
  } catch (error) {
    if (requestId !== orthologRequest) return
    orthologSet.value = null
    comparisonData.value = null
    comparisonLoading.value = false
    sourceError.value = error?.response?.data?.detail || 'Unable to load ortholog relationships.'
  } finally {
    if (requestId === orthologRequest) orthologLoading.value = false
  }
}

const loadComparison = async () => {
  const requestId = ++comparisonRequest
  comparisonError.value = ''
  const geneIds = selectedGeneIds.value
  if (!geneIds.length) {
    comparisonData.value = null
    comparisonLoading.value = false
    return
  }
  const requestKey = selectionKey(geneIds)
  // Read the live DOM before the swap is queued: Vue flushes on nextTick, so
  // the outgoing comparison is still mounted at this point.
  reserveComparisonHeight()
  comparisonLoading.value = true
  try {
    const data = await apiService.compareOrthologGenes(geneIds)
    if (requestId !== comparisonRequest) return
    comparisonData.value = { ...data, forKey: requestKey }
    if (!sampleOptions.value.some(option => option.value === selectedSample.value)) {
      selectedSample.value = ''
      await syncUrl()
    }
  } catch (error) {
    if (requestId === comparisonRequest) {
      comparisonData.value = null
      comparisonError.value = error?.response?.data?.detail || 'Unable to prepare the comparison.'
    }
  } finally {
    if (requestId === comparisonRequest) comparisonLoading.value = false
  }
}

const syncUrl = () =>
  router.replace({
    name: 'CrossSpecies',
    query: {
      gene_db_id: sourceGeneId.value,
      genes: selectedGeneIds.value.join(','),
      ...(selectedSample.value ? { sample: selectedSample.value } : {}),
      ...(viewMode.value === 'gene' ? {} : { view: viewMode.value }),
      ...(axisScale.value === AXIS_SCALE_LINEAR ? {} : { scale: axisScale.value })
    }
  })

const onSelectionChange = ids => {
  selectedGeneIds.value = withSourceFirst(ids)
  syncUrl()
  loadComparison()
}

const onSampleChange = value => {
  selectedSample.value = value || ''
  syncUrl()
}

const onViewModeChange = value => {
  viewMode.value = value
  syncUrl()
}

const onScaleChange = value => {
  axisScale.value = value === AXIS_SCALE_LOG ? AXIS_SCALE_LOG : AXIS_SCALE_LINEAR
  syncUrl()
}

watch(selectedSpecies, () => {
  if (selectedSpecies.value === orthologSet.value?.source_gene?.species) return
  selectedSourceOption.value = null
  geneSuggestions.value = []
})

onMounted(async () => {
  try {
    const species = await apiService.getSpecies()
    speciesOptions.value = species.map(row => ({
      title: row.display_name || row.latin_name || row.name,
      value: row.name
    }))
  } catch {
    speciesOptions.value = [{ title: 'Homo sapiens', value: 'Human' }]
  }

  if (route.query.sample) selectedSample.value = String(route.query.sample)
  if (route.query.view === 'transcript') viewMode.value = 'transcript'
  if (route.query.scale === AXIS_SCALE_LOG) axisScale.value = AXIS_SCALE_LOG

  const routeGeneId = Number(route.query.gene_db_id)
  if (Number.isInteger(routeGeneId) && routeGeneId > 0) {
    await loadOrthologSet(routeGeneId, { restoreFromUrl: true })
  }
})

onBeforeUnmount(() => {
  clearTimeout(geneSearchTimer)
})
</script>

<style scoped>
.compare-page {
  min-height: 100vh;
  background: #f8fafc;
  --compare-title-size: 1.38rem;
  --compare-body-size: 0.92rem;
  --compare-caption-size: 0.82rem;
}
.compare-page :deep(.section-card) { border-radius: 24px; box-shadow: none; }
.compare-page :deep(h2) {
  font-family: var(--aa-font-sans);
  font-size: var(--compare-title-size);
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.3;
}

.hero-section { position: relative; min-height: 300px; display: flex; align-items: center; overflow: hidden; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #0a4f53 0%, #0d7377 42%, #1a2744 100%); }
.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 70% 70% at 72% 30%, rgba(68, 196, 190, 0.18), transparent 70%);
}
.hero-content { position: relative; z-index: 1; padding: 48px 24px 56px; }
.hero-content :deep(.text-h3) {
  font-family: var(--aa-font-sans) !important;
  font-size: 3rem !important;
  font-weight: 700 !important;
  line-height: 1.12;
  letter-spacing: -0.01em !important;
}
.hero-content :deep(.text-h6) {
  max-width: 780px;
  font-family: var(--aa-font-sans) !important;
  font-size: 1.2rem !important;
  font-weight: 500 !important;
  line-height: 1.5;
  letter-spacing: 0 !important;
}
.compare-content { display: flex; flex-direction: column; gap: 28px; padding-top: 40px; padding-bottom: 64px; }

.search-frame { padding: 0 0 22px; overflow: hidden; }
.search-frame-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 24px;
  border-bottom: 1px solid rgba(203, 213, 225, 0.66);
  background: #f1f8f8;
}
.topbar-left { display: flex; align-items: center; gap: 10px; }
.topbar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0d7377, #14919b);
}
.topbar-label { color: var(--aa-slate-700); font-size: 0.88rem; font-weight: 700; }
.topbar-source {
  color: var(--aa-teal-800);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.query-grid {
  display: grid;
  grid-template-columns: minmax(200px, 0.7fr) minmax(300px, 1.3fr) auto;
  gap: 14px;
  align-items: center;
  padding: 22px 24px 0;
}
.compare-field :deep(.v-field) { border-radius: 11px; background: #ffffff; }
.compare-field :deep(.v-field__input) { font-size: var(--compare-body-size); }
.primary-action {
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 22px;
  border: 0;
  border-radius: 10px;
  background: #0d7377;
  color: #ffffff;
  font-size: var(--compare-body-size);
  font-weight: 600;
  cursor: pointer;
  box-shadow: none;
}
.primary-action:disabled { opacity: 0.55; cursor: wait; }

.example-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 16px 24px 0;
  color: var(--aa-slate-500);
  font-size: 0.78rem;
}
.example-chip {
  padding: 5px 11px;
  border: 1px solid rgba(13, 115, 119, 0.2);
  border-radius: 999px;
  background: var(--aa-teal-050);
  color: var(--aa-teal-800);
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.example-chip:hover { border-color: var(--aa-teal-600); background: var(--aa-teal-100); }

.search-frame :deep(.v-alert) { margin: 0 24px; }

.intro-card { padding: 30px 28px; }
.intro-card h2 { margin: 10px 0 8px; color: var(--aa-slate-800); font-size: 1.5rem; line-height: 1.2; }
.intro-lead { margin: 0; color: var(--aa-slate-600); font-size: var(--compare-body-size); line-height: 1.6; }
.intro-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}
.intro-steps li {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 18px;
  border: 1px solid var(--aa-slate-200);
  border-radius: 14px;
  background: #fbfdfd;
}
.intro-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  margin-bottom: 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0d7377, #14919b);
  color: #ffffff;
  font-size: 0.8rem;
  font-weight: 700;
}
.intro-steps strong { color: var(--aa-slate-800); font-size: 0.98rem; }
.intro-steps span:last-child { color: var(--aa-slate-600); font-size: 0.83rem; line-height: 1.5; }

.state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 34px 28px;
  text-align: center;
}
.state-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-bottom: 4px;
  border-radius: 12px;
  background: var(--aa-teal-050);
  color: var(--aa-teal-700);
}
.state-card h3 { margin: 0; color: var(--aa-slate-800); font-size: 1.08rem; font-weight: 700; }
.state-card p { margin: 0; max-width: 560px; color: var(--aa-slate-600); font-size: 0.88rem; line-height: 1.6; }
.state-card--error .state-icon { background: rgba(211, 47, 47, 0.08); color: #c62828; }
.state-card--error h3 { color: #b71c1c; }
.state-action {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  padding: 8px 16px;
  border: 1px solid rgba(13, 115, 119, 0.24);
  border-radius: 999px;
  background: var(--aa-teal-050);
  color: var(--aa-teal-800);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.state-action:hover:not(:disabled) { border-color: var(--aa-teal-600); background: var(--aa-teal-100); }
.state-action:disabled { opacity: 0.55; cursor: not-allowed; }

/*
 * The matrix and the architecture panel used to be direct children of the
 * .compare-content flex column. They are wrapped so their combined height can be
 * measured before a reload, so the wrapper has to repeat the column gap or the
 * spacing between them changes.
 */
.comparison-stack,
.skeleton-stack { display: flex; flex-direction: column; gap: 28px; }
.skeleton-block {
  border: 1px solid rgba(203, 213, 225, 0.72);
  border-radius: var(--aa-radius-lg);
  background: linear-gradient(100deg, #f4f7f9 28%, #eaf1f3 42%, #f4f7f9 56%);
  background-size: 260% 100%;
  animation: skeleton-sweep 1.4s ease-in-out infinite;
}
.skeleton-block--picker { height: 236px; }
.skeleton-block--matrix { height: 268px; }
.skeleton-block--tracks { height: 400px; }

@keyframes skeleton-sweep {
  from { background-position: 140% 0; }
  to { background-position: -40% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-block { animation: none; }
}

@media (max-width: 960px) {
  .query-grid { grid-template-columns: 1fr 1fr; }
  .primary-action { grid-column: 1 / -1; }
}

@media (max-width: 640px) {
  .hero-section { min-height: 270px; }
  .hero-content :deep(.text-h3) { font-size: 2.15rem !important; }
  .hero-content :deep(.text-h6) { font-size: 1rem !important; }
  .compare-content { padding-top: 28px; gap: 18px; }
  .comparison-stack, .skeleton-stack { gap: 18px; }
  .query-grid { grid-template-columns: 1fr; padding: 18px 18px 0; }
  .primary-action { grid-column: auto; }
  .search-frame-topbar { padding: 12px 18px; }
  .example-row { padding: 14px 18px 0; }
  .search-frame :deep(.v-alert) { margin: 0 18px; }
  .intro-card { padding: 20px; }
  .state-card { padding: 26px 20px; }
}
</style>
