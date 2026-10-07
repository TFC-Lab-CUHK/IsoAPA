<template>
  <div class="statistics-page">
    <section class="hero-section">
      <div class="hero-bg"></div>
      <v-container class="hero-content">
        <h1 class="text-h3 font-weight-bold text-white mb-2">IsoAPA Statistics</h1>
        <p class="text-h6 text-white opacity-90">Database-scale view of isoform-level polyadenylation complexity</p>
      </v-container>
    </section>

    <div v-if="loading" class="stats-loading-shell">
      <v-progress-circular indeterminate color="#14919B" size="58"></v-progress-circular>
      <div class="stats-loading-text">Loading database metrics</div>
    </div>

    <v-container v-else-if="error" class="py-10 py-md-12">
      <v-alert type="error" variant="tonal" class="mb-8">
        {{ error }}
      </v-alert>
    </v-container>

    <template v-else>
      <v-container class="stats-content reveal-root">
        <section class="metric-grid reveal-item" style="--delay: 80ms">
          <component
            :is="metric.to ? 'router-link' : 'div'"
            v-for="metric in heroMetrics"
            :key="metric.label"
            class="metric-card"
            :class="{ 'metric-card--link': metric.to }"
            v-bind="metric.to ? { to: metric.to } : {}"
          >
            <div class="metric-icon" :style="{ background: metric.gradient }">
              <v-icon :icon="metric.icon" size="20" color="white"></v-icon>
            </div>
            <div class="metric-value">{{ metric.value }}</div>
            <div class="metric-label">{{ metric.label }}<MetricHelp v-if="metric.definition" :definition="metric.definition" /></div>
            <div class="metric-note">{{ metric.note }}</div>
          </component>
        </section>

        <section class="section-card stats-flow-card reveal-item" style="--delay: 160ms">
          <div class="section-header compact">
            <div>
              <div class="section-eyebrow">Database Depth</div>
              <div class="stats-card-title" role="heading" aria-level="2">Resolution From Gene To Cleavage Site</div>
            </div>
          </div>
          <div class="flow-grid">
            <div class="flow-node">
              <span class="flow-node-value">{{ fmt(detailedStats.total_genes) }}</span>
              <span class="flow-node-label">Genes</span>
            </div>
            <div class="flow-connector">
              <span>avg {{ avgIsoformsPerGene }}x<MetricHelp :definition="COUNT_TERMS.meanIsoforms" /></span>
            </div>
            <div class="flow-node flow-node--strong">
              <span class="flow-node-value">{{ fmt(detailedStats.total_transcripts) }}</span>
              <span class="flow-node-label">Isoforms</span>
            </div>
            <div class="flow-connector">
              <span>avg {{ avgSitesPerIsoform }}x<MetricHelp :definition="COUNT_TERMS.meanPas" /></span>
            </div>
            <div class="flow-node">
              <span class="flow-node-value">{{ fmt(detailedStats.total_apa_sites) }}</span>
              <span class="flow-node-label">PAS clusters<MetricHelp :definition="COUNT_TERMS.pasClusters" /></span>
            </div>
          </div>
        </section>

        <div class="stats-card-row reveal-item" style="--delay: 240ms">
          <div class="stats-card-cell">
            <section class="section-card">
              <div class="section-header stats-filter-header">
                <div class="stats-filter-topline">
                  <div class="section-eyebrow">Regulatory Complexity</div>
                  <v-menu
                    location="bottom end"
                    :close-on-content-click="true"
                    :min-width="260"
                    content-class="stats-species-menu"
                  >
                    <template #activator="{ props }">
                      <button class="species-filter-trigger" type="button" v-bind="props">
                        <span
                          class="species-filter-value"
                          :class="{ 'is-placeholder': !selectedSpecies }"
                        >
                          {{ selectedSpeciesLabel }}
                        </span>
                        <span class="species-filter-icon">
                          <v-progress-circular
                            v-if="speciesLoading"
                            indeterminate
                            size="12"
                            width="2"
                            color="#0D7377"
                          />
                          <v-icon v-else icon="mdi-chevron-down" size="14" />
                        </span>
                      </button>
                    </template>

                    <div class="species-menu-card">
                      <div class="species-menu-header">
                        <span>Select species</span>
                        <small>{{ speciesOptions.length }} choices</small>
                      </div>
                      <button
                        v-for="option in speciesOptions"
                        :key="option.value || 'all'"
                        class="species-menu-option"
                        :class="{ 'is-active': selectedSpecies === option.value }"
                        type="button"
                        @click="selectSpecies(option.value)"
                      >
                        <span class="species-menu-option-main">{{ option.title }}</span>
                        <v-icon
                          v-if="selectedSpecies === option.value"
                          icon="mdi-check"
                          size="17"
                        />
                      </button>
                    </div>
                  </v-menu>
                </div>
                <div>
                  <div class="stats-card-title" role="heading" aria-level="2">PA Site Multiplicity Per Isoform<MetricHelp :definition="COUNT_TERMS.multiplicity" /></div>
                  <p class="section-subtitle">{{ multiplicitySubtitle }}</p>
                </div>
              </div>
              <div class="chart-shell chart-shell--large">
                <div v-if="speciesLoading && !multiplicityStats" class="motif-data-state" role="status">
                  <v-progress-circular indeterminate size="24" width="2" color="#0D7377" />
                  <span>Loading multiplicity data...</span>
                </div>
                <div v-else-if="multiplicityError" class="motif-data-state" role="alert">
                  <span>Unable to load multiplicity data.</span>
                  <button class="motif-retry-button" type="button" @click="reloadSpeciesStats">Retry</button>
                </div>
                <Bar v-else-if="multiplicityChartData" :data="multiplicityChartData" :options="multiplicityChartOptions" />
                <div v-else class="empty-chart">No multiplicity data available</div>
              </div>
              <div v-if="multiplicityStats && !multiplicityError" class="complexity-cards">
                <div class="complexity-card">
                  <span class="complexity-value">{{ pctSingleSite }}%</span>
                  <span class="complexity-label">Single-site isoforms</span>
                </div>
                <div class="complexity-card complexity-card--accent">
                  <span class="complexity-value">{{ pctWithMultiPA }}%</span>
                  <span class="complexity-label">Isoforms with 2+ PA sites</span>
                </div>
                <div class="complexity-card">
                  <span class="complexity-value">{{ fmt(multiplicityBuckets.buckets?.['5+']) }}</span>
                  <span class="complexity-label">Isoforms with 5+ sites</span>
                </div>
              </div>
              <div v-else class="motif-summary-spacer" aria-hidden="true"></div>
            </section>
          </div>

          <div class="stats-card-cell">
            <section class="section-card">
              <div class="section-header stats-filter-header">
                <div class="stats-filter-topline">
                  <div class="section-eyebrow">Motif Composition</div>
                  <v-menu
                    location="bottom end"
                    :close-on-content-click="true"
                    :min-width="260"
                    content-class="stats-species-menu"
                  >
                    <template #activator="{ props }">
                      <button class="species-filter-trigger" type="button" v-bind="props">
                        <span
                          class="species-filter-value"
                          :class="{ 'is-placeholder': !selectedSpecies }"
                        >
                          {{ selectedSpeciesLabel }}
                        </span>
                        <span class="species-filter-icon">
                          <v-progress-circular
                            v-if="speciesLoading"
                            indeterminate
                            size="12"
                            width="2"
                            color="#0D7377"
                          />
                          <v-icon v-else icon="mdi-chevron-down" size="14" />
                        </span>
                      </button>
                    </template>

                    <div class="species-menu-card">
                      <div class="species-menu-header">
                        <span>Select species</span>
                        <small>{{ speciesOptions.length }} choices</small>
                      </div>
                      <button
                        v-for="option in speciesOptions"
                        :key="option.value || 'all'"
                        class="species-menu-option"
                        :class="{ 'is-active': selectedSpecies === option.value }"
                        type="button"
                        @click="selectSpecies(option.value)"
                      >
                        <span class="species-menu-option-main">{{ option.title }}</span>
                        <v-icon
                          v-if="selectedSpecies === option.value"
                          icon="mdi-check"
                          size="17"
                        />
                      </button>
                    </div>
                  </v-menu>
                </div>
                <div>
                  <div class="stats-card-title" role="heading" aria-level="2">PAS Motif Distribution<MetricHelp :definition="COUNT_TERMS.motifCounts" /></div>
                  <p class="section-subtitle">{{ motifSubtitle }}</p>
                </div>
              </div>
              <div class="chart-shell chart-shell--large motif-chart-shell">
                <div
                  v-if="speciesLoading && !motifStats"
                  class="motif-data-state"
                  role="status"
                >
                  <v-progress-circular
                    indeterminate
                    size="24"
                    width="2"
                    color="#0D7377"
                  />
                  <span>Loading PAS motif data...</span>
                </div>
                <div
                  v-else-if="motifError"
                  class="motif-data-state"
                  role="alert"
                >
                  <span>Unable to load PAS motif data.</span>
                  <button class="motif-retry-button" type="button" @click="reloadSpeciesStats">
                    Retry
                  </button>
                </div>
                <div
                  v-else-if="motifAssessmentUnavailable"
                  class="motif-assessment-state"
                  role="status"
                >
                  <span class="motif-assessment-icon" aria-hidden="true">
                    <v-icon icon="mdi-chart-donut" size="22" />
                  </span>
                  <span>PAS motif model not assessed for this lineage.</span>
                </div>
                <Pie v-else-if="motifChartData" :data="motifChartData" :options="motifChartOptions" />
                <div v-else class="empty-chart">No PAS motif data available</div>
              </div>
              <div v-if="!motifSummaryHidden" class="complexity-cards motif-summary-cards">
                <div class="complexity-card">
                  <span class="complexity-value">{{ fmt(motifStats?.total) }}</span>
                  <span class="complexity-label">PAS clusters</span>
                </div>
                <div class="complexity-card complexity-card--accent">
                  <span class="complexity-value">{{ noMotifPct }}%</span>
                  <span class="complexity-label">Sites with no motif</span>
                </div>
                <div class="complexity-card">
                  <span class="complexity-value">{{ topMotifPct }}%</span>
                  <span class="complexity-label">{{ topMotifLabel }} share</span>
                </div>
              </div>
              <div
                v-else
                class="motif-summary-spacer"
                aria-hidden="true"
              ></div>
            </section>
          </div>
        </div>

        <section id="pas-evidence" class="section-card evidence-card reveal-item" style="--delay: 320ms">
          <div class="section-header stats-filter-header">
            <div class="stats-filter-topline">
              <div class="section-eyebrow">Annotation Context</div>
              <v-menu location="bottom end" :close-on-content-click="true" :min-width="260" content-class="stats-species-menu">
                <template #activator="{ props }">
                  <button
                    class="species-filter-trigger"
                    type="button"
                    :aria-label="`Species for PAS evidence: ${selectedSpeciesLabel}`"
                    v-bind="props"
                  >
                    <span class="species-filter-value" :class="{ 'is-placeholder': !selectedSpecies }">{{ selectedSpeciesLabel }}</span>
                    <span class="species-filter-icon">
                      <v-progress-circular v-if="speciesLoading" indeterminate size="12" width="2" color="#0D7377" />
                      <v-icon v-else icon="mdi-chevron-down" size="14" />
                    </span>
                  </button>
                </template>
                <div class="species-menu-card">
                  <div class="species-menu-header">
                    <span>Select species</span>
                    <small>{{ speciesOptions.length }} choices</small>
                  </div>
                  <button
                    v-for="option in speciesOptions"
                    :key="option.value"
                    class="species-menu-option"
                    :class="{ 'is-active': selectedSpecies === option.value }"
                    type="button"
                    @click="selectSpecies(option.value)"
                  >
                    <span class="species-menu-option-main">{{ option.title }}</span>
                    <v-icon v-if="selectedSpecies === option.value" icon="mdi-check" size="17" />
                  </button>
                </div>
              </v-menu>
            </div>
            <div class="evidence-title-row">
              <div class="stats-card-title" role="heading" aria-level="2">PAS Evidence Levels</div>
              <v-tooltip
                location="top"
                max-width="340"
                content-class="pas-evidence-tooltip"
                :open-on-hover="evidenceHoverCapable"
                :open-on-click="!evidenceHoverCapable"
                :open-on-focus="true"
              >
                <template #activator="{ props }">
                  <button class="evidence-info" type="button" aria-label="About PAS evidence levels" v-bind="props">
                    <v-icon icon="mdi-help-circle-outline" size="17" />
                  </button>
                </template>
                <div v-for="(style, level) in evidenceStyles" :key="level" class="evidence-tooltip-row">
                  <strong>{{ level }}</strong><span>{{ style.description }}</span>
                </div>
                <p class="evidence-tooltip-note">
                  Recurrence means detection in at least two sample groups. Levels describe supporting evidence, not probabilities of correctness.
                </p>
              </v-tooltip>
            </div>
          </div>

          <div v-if="!selectedSpecies" class="evidence-state" role="status">
            Choose a species to view its evidence levels.
          </div>
          <div v-else-if="speciesLoading" class="evidence-state" role="status">
            <v-progress-circular indeterminate size="22" width="2" color="#0D7377" />
            Loading evidence summary...
          </div>
          <div v-else-if="evidenceError" class="evidence-state" role="alert">
            Unable to load this species.
            <button class="motif-retry-button" type="button" @click="reloadSpeciesStats">Retry</button>
          </div>
          <div v-else-if="evidenceStats" class="evidence-content">
            <div class="evidence-context">
              <span><strong>{{ fmt(evidenceStats.sample_group_count) }}</strong> {{ evidenceStats.sample_group_count === 1 ? 'sample group' : 'sample groups' }}</span>
              <span>Motif model: <strong>{{ evidenceStats.motif_model_label }}</strong></span>
              <span><strong>{{ fmt(evidenceStats.total_clusters) }}</strong> unique PAS clusters</span>
            </div>
            <div class="evidence-bar" aria-hidden="true">
              <span
                v-for="level in evidenceLevels"
                :key="level.level"
                :style="{ width: `${evidenceStats.total_clusters ? 100 * level.count / evidenceStats.total_clusters : 0}%`, background: level.color }"
              ></span>
            </div>
            <div class="evidence-levels">
              <div v-for="level in evidenceLevels" :key="level.level" class="evidence-level">
                <span class="evidence-level-name" :title="level.description">
                  <i :style="{ background: level.color }" aria-hidden="true"></i>{{ level.level }}
                </span>
                <span class="evidence-level-count">{{ fmt(level.count) }} <small>{{ level.pct.toFixed(1) }}%</small></span>
              </div>
            </div>
            <p v-if="evidenceNote" class="evidence-note" role="status">
              <v-icon icon="mdi-information-outline" size="15" />{{ evidenceNote }}
            </p>
            <p v-if="evidenceStats.unassigned_count" class="evidence-note">
              {{ fmt(evidenceStats.unassigned_count) }} clusters have no assigned evidence level.
            </p>
          </div>
        </section>

        <div class="stats-card-row reveal-item" style="--delay: 400ms">
          <div class="stats-card-cell">
            <section class="section-card">
              <div class="section-header stats-filter-header">
                <div>
                  <div class="section-eyebrow">Taxonomic Scope</div>
                  <div class="stats-card-title" role="heading" aria-level="2">Top 10 Species Richness<MetricHelp :definition="COUNT_TERMS.pasClusters" /></div>
                  <p class="section-subtitle">Species ranked by unique PAS cluster count.</p>
                </div>
              </div>
              <div class="leaderboard-container">
                <div v-for="(sp, i) in speciesRichnessData" :key="sp.name" class="leaderboard-row">
                  <div class="rank-badge" :class="rankClass(i)">{{ i + 1 }}</div>
                  <div class="species-leader-name">
                    <div class="species-common">{{ sp.displayName }}</div>
                    <div v-if="sp.subtitle" class="species-latin">{{ sp.subtitle }}</div>
                  </div>
                  <div class="leaderboard-bar-track">
                    <div class="leaderboard-bar-fill species-leader-bar-fill" :style="{ width: sp.pct + '%' }"></div>
                  </div>
                  <v-chip size="small" color="#14919B" variant="tonal" class="font-weight-bold">{{ fmt(sp.apaCount) }}</v-chip>
                </div>
                <div v-if="!speciesRichnessData.length" class="empty-chart py-8">No species data available</div>
              </div>
            </section>
          </div>

          <div class="stats-card-cell">
            <section class="section-card">
              <div class="section-header stats-filter-header">
                <div class="stats-filter-topline">
                  <div class="section-eyebrow">Database Highlights</div>
                  <v-menu
                    location="bottom end"
                    :close-on-content-click="true"
                    :min-width="260"
                    content-class="stats-species-menu"
                  >
                    <template #activator="{ props }">
                      <button class="species-filter-trigger" type="button" v-bind="props">
                        <span
                          class="species-filter-value"
                          :class="{ 'is-placeholder': !selectedSpecies }"
                        >
                          {{ selectedSpeciesLabel }}
                        </span>
                        <span class="species-filter-icon">
                          <v-progress-circular
                            v-if="speciesLoading"
                            indeterminate
                            size="12"
                            width="2"
                            color="#0D7377"
                          />
                          <v-icon v-else icon="mdi-chevron-down" size="14" />
                        </span>
                      </button>
                    </template>

                    <div class="species-menu-card">
                      <div class="species-menu-header">
                        <span>Select species</span>
                        <small>{{ speciesOptions.length }} choices</small>
                      </div>
                      <button
                        v-for="option in speciesOptions"
                        :key="option.value || 'all'"
                        class="species-menu-option"
                        :class="{ 'is-active': selectedSpecies === option.value }"
                        type="button"
                        @click="selectSpecies(option.value)"
                      >
                        <span class="species-menu-option-main">{{ option.title }}</span>
                        <v-icon
                          v-if="selectedSpecies === option.value"
                          icon="mdi-check"
                          size="17"
                        />
                      </button>
                    </div>
                  </v-menu>
                </div>
                <div>
                  <div class="stats-card-title" role="heading" aria-level="2">Top 10 Gene Richness<MetricHelp :definition="COUNT_TERMS.genePasClusters" /></div>
                  <p class="section-subtitle">Genes ranked by unique PAS cluster count.</p>
                </div>
              </div>
              <div ref="geneListElement" class="leaderboard-container">
                <div v-if="speciesLoading && !topGeneStats" class="gene-data-state motif-data-state" :style="{ minHeight: `${geneLoadingHeight}px` }" role="status">
                  <v-progress-circular indeterminate size="24" width="2" color="#0D7377" />
                  <span>Loading gene data...</span>
                </div>
                <div v-else-if="topGeneError" class="gene-data-state motif-data-state" :style="{ minHeight: `${geneLoadingHeight}px` }" role="alert">
                  <span>Unable to load gene data.</span>
                  <button class="motif-retry-button" type="button" @click="reloadSpeciesStats">Retry</button>
                </div>
                <template v-else>
                <div v-for="(gene, i) in topGenesByApa" :key="`${gene.gene_db_id}-${gene.species}`" class="leaderboard-row">
                  <div class="rank-badge" :class="rankClass(i)">{{ i + 1 }}</div>
                  <router-link
                    :to="{ name: 'GeneDetail', params: { geneId: gene.gene_db_id }, query: { species: gene.species } }"
                    class="gene-name-link"
                  >
                    {{ gene.gene_name || 'Unknown' }}
                  </router-link>
                  <span class="gene-species-chip">{{ formatSpeciesName(gene.species) }}</span>
                  <div class="leaderboard-bar-track">
                    <div class="leaderboard-bar-fill" :style="{ width: ((gene.apa_count / maxGeneApaCount) * 100) + '%' }"></div>
                  </div>
                  <v-chip size="small" color="#14919B" variant="tonal" class="font-weight-bold">{{ fmt(gene.apa_count) }}</v-chip>
                </div>
                <div v-if="!topGenesByApa.length" class="empty-chart py-8">No top genes available</div>
                </template>
              </div>
            </section>
          </div>
        </div>
      </v-container>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Bar, Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Title
} from 'chart.js'
import { apiService } from '@/services/api'
import { formatSpeciesName, formatSpeciesSubtitle } from '@/utils/formatters'
import MetricHelp from '@/components/MetricHelp.vue'
import { COUNT_TERMS } from '@/constants/countingTerms'
import { useLinkedSpeciesStats } from '@/composables/useLinkedSpeciesStats'

ChartJS.register(BarElement, ArcElement, CategoryScale, LinearScale, Tooltip, Legend, Title)

const loading = ref(true)
const error = ref(null)
const detailedStats = ref({})
const speciesList = ref([])
const {
  selectedSpecies,
  loading: speciesLoading,
  results: speciesResults,
  errors: speciesErrors,
  selectSpecies: updateSelectedSpecies,
  reload: reloadLinkedStats,
  dispose: disposeSpeciesStats
} = useLinkedSpeciesStats(apiService, () => detailedStats.value)

const geneListElement = ref(null)
const geneLoadingHeight = ref(430)
const reserveGeneListHeight = () => { geneLoadingHeight.value = geneListElement.value?.offsetHeight || 430 }
const selectSpecies = species => {
  reserveGeneListHeight()
  return updateSelectedSpecies(species)
}
const reloadSpeciesStats = () => {
  reserveGeneListHeight()
  return reloadLinkedStats()
}

const multiplicityStats = computed(() => speciesResults.value.multiplicity)
const motifStats = computed(() => speciesResults.value.motif)
const evidenceStats = computed(() => speciesResults.value.evidence)
const topGeneStats = computed(() => speciesResults.value.genes)
const multiplicityError = computed(() => speciesErrors.value.multiplicity)
const motifError = computed(() => speciesErrors.value.motif)
const evidenceError = computed(() => speciesErrors.value.evidence)
const topGeneError = computed(() => speciesErrors.value.genes)
onUnmounted(disposeSpeciesStats)

const evidenceHoverQuery = typeof window !== 'undefined' ? window.matchMedia('(hover: hover)') : null
const evidenceHoverCapable = ref(evidenceHoverQuery?.matches ?? true)
const updateEvidenceHover = event => { evidenceHoverCapable.value = event.matches }
onMounted(() => evidenceHoverQuery?.addEventListener('change', updateEvidenceHover))
onUnmounted(() => evidenceHoverQuery?.removeEventListener('change', updateEvidenceHover))

const fmt = (value) => Number(value ?? 0).toLocaleString()

onMounted(async () => {
  try {
    const [detailed, species] = await Promise.all([
      apiService.getDetailedStats(),
      apiService.getSpecies()
    ])
    detailedStats.value = detailed || {}
    speciesList.value = species || []
  } catch (err) {
    console.error('Failed to load stats:', err)
    error.value = 'Failed to load statistics. Please try again.'
  } finally {
    loading.value = false
  }
  if (!error.value) await reloadSpeciesStats()
})

const speciesOptions = computed(() => [
  { title: 'All species', value: '' },
  ...speciesList.value.map(sp => ({ title: sp.display_name || formatSpeciesName(sp), value: sp.name }))
])
const selectedSpeciesLabel = computed(() => selectedSpecies.value
  ? speciesOptions.value.find(option => option.value === selectedSpecies.value)?.title || formatSpeciesName(selectedSpecies.value)
  : 'Species'
)

const evidenceStyles = {
  'PAS-L1': { color: '#0D7377', description: 'Cross-sample recurrence and primary motif support.' },
  'PAS-L2': { color: '#D3A05C', description: 'Cross-sample recurrence or primary motif support, but not both.' },
  'PAS-L3': { color: '#8C89B0', description: 'Retained PAS without either additional form of support.' }
}
const evidenceLevels = computed(() => (evidenceStats.value?.levels || []).map(level => ({
  ...level, ...evidenceStyles[level.level]
})))
const evidenceNote = computed(() => {
  const stats = evidenceStats.value
  if (!stats) return ''
  const reasons = stats.l1_unavailable_reasons || []
  const limitedSamples = reasons.includes('insufficient_sample_groups')
  const unassessed = reasons.includes('motif_not_assessed')
  const sampleReason = stats.sample_group_count === 1 ? 'only one sample group' : 'no sample groups'
  if (limitedSamples && unassessed) return `PAS-L1 unavailable: ${sampleReason} and no motif assessment.`
  if (limitedSamples) return `PAS-L1 unavailable: ${sampleReason}.`
  if (unassessed) return 'PAS-L1 unavailable: motif assessment has not been performed.'
  if (stats.motif_assessed === null) return 'Motif model information is not recorded for this species.'
  return ''
})

const avgIsoformsPerGene = computed(() => detailedStats.value.avg_isoforms_per_gene ?? '—')
const avgSitesPerIsoform = computed(() => detailedStats.value.avg_apa_per_transcript ?? '—')
const multiplicityBuckets = computed(() => multiplicityStats.value || { buckets: {}, total: 0 })
const pctWithMultiPA = computed(() => multiplicityBuckets.value.pct_multi_site ?? 0)
const pctSingleSite = computed(() => multiplicityBuckets.value.pct_single_site ?? 0)
const multiplicitySubtitle = computed(() => {
  if (!selectedSpecies.value) {
    return 'Distinct PASs per isoform across sample groups.'
  }
  const selected = speciesList.value.find(sp => sp.name === selectedSpecies.value)
  return `Cross-sample PAS counts for ${selected ? formatSpeciesName(selected) : formatSpeciesName(selectedSpecies.value)} isoforms.`
})
const motifSubtitle = computed(() => {
  if (!selectedSpecies.value) {
    return 'Distribution of annotated PAS motifs across all PA site clusters.'
  }
  const selected = speciesList.value.find(sp => sp.name === selectedSpecies.value)
  return `Distribution for ${selected ? formatSpeciesName(selected) : formatSpeciesName(selectedSpecies.value)} PA sites.`
})

const heroMetrics = computed(() => [
  {
    label: 'Species',
    value: fmt(detailedStats.value.total_species),
    note: 'organisms loaded',
    icon: 'mdi-paw',
    gradient: 'linear-gradient(135deg,#0D7377,#14919B)',
    to: { name: 'Help', hash: '#references', query: { open: 'references' } }
  },
  {
    label: 'Isoforms',
    value: fmt(detailedStats.value.total_transcripts),
    note: 'observed reference transcripts',
    definition: COUNT_TERMS.isoforms,
    icon: 'mdi-file-tree-outline',
    gradient: 'linear-gradient(135deg,#355C7D,#4A7898)'
  },
  {
    label: COUNT_TERMS.pasClusters.label,
    value: fmt(detailedStats.value.total_apa_sites),
    note: 'unique within each species',
    definition: COUNT_TERMS.pasClusters,
    icon: 'mdi-map-marker-multiple-outline',
    gradient: 'linear-gradient(135deg,#2F855A,#48A36D)'
  },
  {
    label: COUNT_TERMS.sampleGroups.label,
    value: fmt(detailedStats.value.total_samples),
    note: 'harmonised biological sources',
    definition: COUNT_TERMS.sampleGroups,
    icon: 'mdi-flask-outline',
    gradient: 'linear-gradient(135deg,#A96F4C,#B7791F)'
  }
])

const chartTooltip = {
  backgroundColor: 'rgba(248, 252, 252, 0.96)',
  titleColor: '#0f172a',
  bodyColor: '#334155',
  borderColor: 'rgba(13, 115, 119, 0.18)',
  borderWidth: 1,
  padding: 12,
  titleFont: { family: 'IBM Plex Sans', size: 13, weight: '700' },
  bodyFont: { family: 'IBM Plex Sans', size: 13, weight: '500' }
}

const multiplicityChartData = computed(() => {
  const buckets = multiplicityBuckets.value.buckets || {}
  if (!multiplicityBuckets.value.total) return null
  return {
    labels: ['1 PA site', '2 PA sites', '3 PA sites', '4 PA sites', '5+ PA sites'],
    datasets: [{
      label: 'Isoforms',
      data: [buckets['1'] || 0, buckets['2'] || 0, buckets['3'] || 0, buckets['4'] || 0, buckets['5+'] || 0],
      backgroundColor: ['#94a3b8', '#6fa8a8', '#14919B', '#0D7377', '#0A5C5F'],
      hoverBackgroundColor: ['#64748b', '#568f90', '#0D7377', '#0A5C5F', '#064346'],
      categoryPercentage: 0.70,
      barPercentage: 0.66,
      borderRadius: 0,
      borderSkipped: false
    }]
  }
})

const multiplicityChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 900, easing: 'easeOutQuart' },
  plugins: {
    legend: { display: false },
    tooltip: {
      ...chartTooltip,
      callbacks: {
        afterLabel: (ctx) => {
          const total = multiplicityBuckets.value.total
          const pct = total ? ((ctx.raw / total) * 100).toFixed(1) : 0
          return `${pct}% of all isoforms`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      border: { display: true, color: 'rgba(100, 116, 139, 0.34)' },
      grid: { display: false, drawBorder: false },
      ticks: {
        color: '#64748b',
        padding: 8,
        font: { family: 'IBM Plex Sans', size: 11, weight: '500' }
      }
    },
    x: {
      border: { display: true, color: 'rgba(100, 116, 139, 0.34)' },
      grid: { display: false, drawBorder: false },
      ticks: {
        color: '#475569',
        padding: 8,
        font: { family: 'IBM Plex Sans', size: 12, weight: '700' }
      }
    }
  }
}))

const motifColors = [
  '#66C2A5', '#C5A07A', '#DE927F', '#979EC1', '#BE94C7', '#DB98AF',
  '#B2CA68', '#CED843', '#FDD738', '#ECCA78', '#D3BE9F', '#B3B3B3'
]

const motifColor = (motif, index) => {
  if (motif === 'Not assessed') return '#D1D5DB'
  if (motif === 'No motif') return '#B8C2CC'
  if (motif === 'Other motifs') return '#8FA1AF'
  return motifColors[index % motifColors.length]
}

const motifAssessmentUnavailable = computed(() => {
  const motifs = motifStats.value?.motifs
  const total = Number(motifStats.value?.total)

  return Boolean(selectedSpecies.value) &&
    total > 0 &&
    Array.isArray(motifs) &&
    motifs.length === 1 &&
    motifs[0]?.motif === 'Not assessed' &&
    Number(motifs[0]?.count) === total
})

const motifSummaryHidden = computed(() =>
  (speciesLoading.value && !motifStats.value) || Boolean(motifError.value) || motifAssessmentUnavailable.value
)

const motifChartData = computed(() => {
  const motifs = motifStats.value?.motifs || []
  if (motifAssessmentUnavailable.value || !motifs.length) return null
  return {
    labels: motifs.map(item => item.motif),
    datasets: [{
      data: motifs.map(item => item.count),
      backgroundColor: motifs.map((item, i) => motifColor(item.motif, i)),
      hoverBackgroundColor: motifs.map((item, i) => motifColor(item.motif, i)),
      borderColor: '#ffffff',
      borderWidth: 3,
      hoverOffset: 8
    }]
  }
})

const noMotifPct = computed(() =>
  motifStats.value?.motifs?.find(item => item.motif === 'No motif')?.pct ?? 0
)

const topMotif = computed(() =>
  motifStats.value?.motifs?.find(item => !['No motif', 'Other motifs', 'Not assessed'].includes(item.motif)) || null
)

const topMotifLabel = computed(() => topMotif.value?.motif || 'Top motif')
const topMotifPct = computed(() => topMotif.value?.pct ?? 0)

const motifChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 900, easing: 'easeOutQuart' },
  plugins: {
    legend: {
      position: 'right',
      labels: {
        boxWidth: 10,
        boxHeight: 10,
        padding: 12,
        color: '#475569',
        font: { family: 'IBM Plex Sans', size: 11, weight: '600' }
      }
    },
    tooltip: {
      ...chartTooltip,
      callbacks: {
        label: (ctx) => {
          const item = motifStats.value?.motifs?.[ctx.dataIndex]
          return `${ctx.label}: ${fmt(ctx.raw)} sites (${item?.pct ?? 0}%)`
        }
      }
    }
  }
}))

const speciesRichnessData = computed(() => {
  const speciesMeta = new Map(speciesList.value.map(sp => [sp.name, sp]))
  const rows = detailedStats.value.apa_sites_by_species || []
  const maxCount = Math.max(...rows.map(s => s.count), 1)
  const colors = ['#0D7377', '#14919B', '#355C7D', '#2F855A', '#A96F4C', '#746A9E']
  return rows
    .map((row, i) => {
      const meta = speciesMeta.get(row.name) || row
      return {
        ...row,
        displayName: row.display_name || formatSpeciesName(meta),
        subtitle: formatSpeciesSubtitle(meta),
        assembly: meta.assembly,
        apaCount: row.count,
        pct: (row.count / maxCount) * 100,
        color: colors[i % colors.length]
      }
    })
    .sort((a, b) => b.apaCount - a.apaCount)
    .slice(0, 10)
})

const maxGeneApaCount = computed(() =>
  Math.max(...(topGenesByApa.value.map(g => g.apa_count) ?? [1]), 1)
)

const topGenesByApa = computed(() =>
  topGeneStats.value || []
)

const rankClass = (i) => {
  if (i === 0) return 'rank-gold'
  if (i === 1) return 'rank-silver'
  if (i === 2) return 'rank-bronze'
  return 'rank-default'
}

</script>

<style scoped>
.statistics-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc 0%, #f4f8fa 100%);
}

.stats-loading-shell {
  min-height: 460px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
}

.stats-loading-text {
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.025em;
}

.reveal-item {
  opacity: 0;
  transform: translateY(12px) scale(0.992);
  animation: statsReveal 560ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: var(--delay, 0ms);
  will-change: opacity, transform;
}

@keyframes statsReveal {
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.hero-section {
  position: relative;
  min-height: 300px;
  display: flex;
  align-items: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #0a4f53 0%, #0D7377 40%, #1a2744 100%);
  background-size: 300% 300%;
  animation: gradientShift 18s ease infinite;
}
.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 80% 60% at 60% 40%, rgba(20,145,155,0.18) 0%, transparent 70%);
}

.hero-content {
  position: relative;
  z-index: 1;
  padding: 48px 24px 56px;
}

.hero-content :deep(.text-h3) {
  font-family: var(--aa-font-sans) !important;
  font-size: 3rem !important;
  font-weight: 700 !important;
  line-height: 1.12;
  letter-spacing: -0.01em !important;
}

.hero-content :deep(.text-h6) {
  font-family: var(--aa-font-sans) !important;
  max-width: 760px;
  font-size: 1.25rem !important;
  font-weight: 500 !important;
  line-height: 1.45;
  letter-spacing: 0 !important;
}

.stats-content {
  position: relative;
  padding-top: 48px;
  padding-bottom: 56px;
  --stats-card-gap: 28px;
  display: flex;
  flex-direction: column;
  gap: var(--stats-card-gap);
}

/*
.stats-hero {
  position: relative;
  overflow: hidden;
  min-height: 300px;
  display: flex;
  align-items: center;
  padding: 0;
  color: white;
  background: linear-gradient(135deg, #0a4f53 0%, #0D7377 40%, #1a2744 100%);
  background-size: 300% 300%;
  animation: gradientShift 18s ease infinite;
}

.stats-hero-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 80% 60% at 60% 40%, rgba(20,145,155,0.18) 0%, transparent 70%);
  pointer-events: none;
}
*/

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.stats-hero-container {
  position: relative;
  min-height: 300px;
  display: flex;
  align-items: center;
  padding-top: 48px;
  padding-bottom: 56px;
}

.stats-hero-copy {
  position: relative;
  z-index: 1;
  max-width: 760px;
}

.stats-title {
  font-size: 3rem;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin: 8px 0 10px;
}

.stats-subtitle {
  max-width: 680px;
  color: rgba(255,255,255,0.90);
  font-size: 1.25rem;
  line-height: 1.45;
}

.cache-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.22);
  color: rgba(255,255,255,0.86);
  font-size: 0.78rem;
  font-weight: 700;
}

.hero-orbit {
  position: absolute;
  right: clamp(24px, 7vw, 90px);
  top: 50%;
  width: 220px;
  height: 220px;
  transform: translateY(-50%);
  opacity: 0.78;
}

.orbit-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.22);
}

.orbit-ring--inner { inset: 48px; }
.orbit-dot {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #9FE7E3;
  box-shadow: 0 0 34px rgba(159,231,227,0.8);
}
.orbit-dot--a { top: 22px; right: 48px; }
.orbit-dot--b { bottom: 40px; left: 26px; background: #E6B06D; }

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin: 0;
  position: relative;
}

.metric-card,
.section-card {
  background: #fff;
  border: 1px solid rgba(203, 213, 225, 0.72);
  box-shadow: none;
}

.statistics-page .section-card,
.statistics-page .stats-card-cell > .section-card {
  background: #ffffff !important;
  background-image: none !important;
  border: 1px solid rgba(203, 213, 225, 0.72) !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
}

.metric-card {
  border-radius: 22px;
  padding: 22px;
  transition: transform 180ms ease, border-color 180ms ease, background-color 180ms ease;
}

.metric-card--link {
  color: inherit;
  cursor: pointer;
  text-decoration: none;
}

.metric-card--link:hover {
  border-color: rgba(20, 145, 155, 0.34);
  transform: translateY(-2px);
}

.metric-card--link:focus-visible {
  outline: 3px solid rgba(20, 145, 155, 0.22);
  outline-offset: 3px;
}

.metric-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.metric-value {
  font-family: var(--aa-font-display);
  font-size: clamp(1.65rem, 2.8vw, 2.35rem);
  line-height: 1.05;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.012em;
}

.metric-label {
  display: flex;
  align-items: center;
  min-height: 20px;
  margin-top: 8px;
  color: #0D7377;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.72rem;
}

.metric-note {
  color: #64748b;
  font-size: 0.85rem;
  margin-top: 5px;
}

.section-card {
  border-radius: 24px;
  padding: 24px;
  margin-bottom: 0;
}

.stats-card-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--stats-card-gap);
  align-items: stretch;
}

.evidence-card .section-header { margin-bottom: 12px; }
.evidence-title-row { display: flex; align-items: center; gap: 8px; }
.evidence-info { color: #64748b; display: inline-flex; padding: 3px; border-radius: 4px; }
.evidence-info:focus-visible { outline: 2px solid #0D7377; outline-offset: 2px; }
:global(.v-tooltip > .v-overlay__content.pas-evidence-tooltip) {
  background: #f8fafc;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 13px 15px;
  font-size: 0.82rem;
  line-height: 1.5;
}
.evidence-tooltip-row { display: grid; grid-template-columns: 49px minmax(0, 1fr); gap: 10px; }
.evidence-tooltip-row + .evidence-tooltip-row { margin-top: 8px; }
.evidence-tooltip-row strong { white-space: nowrap; font-weight: 600; }
.evidence-tooltip-note { border-top: 1px solid #e2e8f0; margin: 10px 0 0; padding-top: 9px; }
.evidence-content { min-height: 108px; }
.evidence-context { display: flex; flex-wrap: wrap; gap: 6px 24px; color: #64748b; font-size: 0.85rem; }
.evidence-context strong { color: #475569; font-weight: 600; }
.evidence-bar { display: flex; height: 12px; overflow: hidden; border-radius: 4px; background: #f1f5f9; margin: 18px 0 14px; }
.evidence-bar > span + span { box-shadow: inset 1px 0 #ffffff; }
.evidence-levels { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
.evidence-level { min-width: 0; }
.evidence-level-name { display: flex; align-items: center; gap: 7px; color: #475569; font-size: 0.8rem; font-weight: 600; }
.evidence-level-name i { width: 8px; height: 8px; border-radius: 2px; }
.evidence-level-count { display: flex; flex-wrap: wrap; align-items: baseline; gap: 9px; margin-top: 4px; color: #1e293b; font-size: 1.3rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.evidence-level-count small { color: #64748b; font-size: 0.85rem; font-weight: 400; }
.evidence-note { display: flex; align-items: baseline; gap: 6px; margin-top: 14px; color: #64748b; font-size: 0.83rem; line-height: 1.5; }
.evidence-note .v-icon { flex-shrink: 0; align-self: center; }
.evidence-state { min-height: 108px; display: flex; align-items: center; justify-content: center; gap: 12px; color: #64748b; font-size: 0.9rem; }
@media (max-width: 600px) {
  .evidence-card .stats-filter-topline { flex-wrap: wrap; }
  .evidence-levels { gap: 12px; }
  .evidence-level-count { gap: 2px 8px; font-size: 1.15rem; }
}

.stats-card-cell,
.stats-card-cell > .section-card {
  min-width: 0;
  height: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 20px;
}

.section-header.compact { margin-bottom: 18px; }
.stats-filter-header {
  display: block;
}

.stats-filter-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 4px;
}

.stats-filter-topline .section-eyebrow {
  min-height: 24px;
  padding-top: 0;
  padding-bottom: 0;
  line-height: 1;
}

.species-filter-trigger {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex: 0 0 auto;
  height: 24px;
  padding: 0 7px 0 9px;
  border: 1px solid rgba(13, 115, 119, 0.20);
  border-radius: 8px;
  background: #f8fcfc;
  box-shadow: none;
  color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition: border-color 160ms ease, background 160ms ease;
}

.species-filter-trigger:hover {
  border-color: rgba(13, 115, 119, 0.34);
  background: #eff8f8;
}

.species-filter-value {
  min-width: 0;
  color: #1e293b;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.10em;
  line-height: 1;
  text-transform: uppercase;
  white-space: nowrap;
}

.species-filter-value.is-placeholder {
  color: #0D7377;
}

.species-filter-icon {
  width: 15px;
  height: 15px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.08);
}

:global(.stats-species-menu) {
  width: 280px !important;
  max-width: min(280px, calc(100vw - 32px));
  opacity: 0;
  transform: translateY(-6px) scale(0.985);
  transform-origin: top right;
  animation: statsDropdownIn 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  will-change: opacity, transform;
}

@keyframes statsDropdownIn {
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.species-menu-card {
  max-height: 280px;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid rgba(13, 115, 119, 0.16);
  border-radius: 14px;
  background: #fff;
  box-shadow: none;
}

.species-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  padding: 8px 10px 10px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.86);
  color: #1e293b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.species-menu-header small {
  color: #94a3b8;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: none;
}

.species-menu-option {
  width: 100%;
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 5px;
  padding: 8px 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: background 140ms ease, color 140ms ease, transform 140ms ease;
}

.species-menu-option:hover {
  transform: translateX(2px);
  background: rgba(13, 115, 119, 0.07);
  color: #0D7377;
}

.species-menu-option.is-active {
  background: linear-gradient(135deg, rgba(13, 115, 119, 0.12), rgba(20, 145, 155, 0.08));
  color: #0D7377;
}

.species-menu-option-main {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  font-weight: 600;
}
.section-eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: #14919B;
}
.section-eyebrow--light { color: rgba(172, 244, 240, 0.95); }
.stats-card-title {
  font-family: var(--aa-font-sans);
  font-size: 1.38rem;
  font-weight: 600;
  font-stretch: normal;
  color: #1e293b;
  letter-spacing: 0.025em;
  font-variation-settings: normal;
  margin: 4px 0 6px;
  line-height: 1.3;
}
.section-subtitle {
  color: #64748b;
  font-size: 0.92rem;
  line-height: 1.55;
  max-width: 720px;
}

.flow-grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  align-items: stretch;
  gap: 14px;
}

.flow-node,
.flow-connector {
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flow-node {
  min-height: 118px;
  flex-direction: column;
  background: #f8fafc;
  border: 1px solid rgba(13, 115, 119, 0.14);
}

.flow-node--strong { border-color: rgba(20, 145, 155, 0.34); }
.flow-node-value {
  color: #0D7377;
  font-family: var(--aa-font-display);
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.flow-node-label {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  color: #64748b;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 0.74rem;
}
.flow-connector {
  min-width: 110px;
  color: #475569;
  font-weight: 700;
  font-size: 0.82rem;
  position: relative;
}
.flow-connector::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  border-top: 1px dashed rgba(13, 115, 119, 0.26);
}
.flow-connector span {
  position: relative;
  background: #fff;
  padding: 4px 8px;
  border-radius: 999px;
}

.chart-shell {
  height: 280px;
  padding: 8px 0 0;
}
.chart-shell--large { height: 315px; }
.chart-shell--wide { height: 400px; }
.motif-chart-shell {
  padding-top: 4px;
}
.motif-data-state,
.motif-assessment-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  font-size: 0.92rem;
  font-weight: 600;
  text-align: center;
}
.motif-retry-button {
  min-height: 32px;
  padding: 5px 14px;
  border: 1px solid rgba(13, 115, 119, 0.34);
  border-radius: 6px;
  color: #0D7377;
  background: #fff;
  font: inherit;
  font-size: 0.8rem;
  cursor: pointer;
}
.motif-retry-button:hover,
.motif-retry-button:focus-visible {
  background: rgba(13, 115, 119, 0.07);
  border-color: rgba(13, 115, 119, 0.56);
}
.motif-retry-button:focus-visible {
  outline: 2px solid rgba(13, 115, 119, 0.28);
  outline-offset: 2px;
}
.motif-assessment-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.08);
  border: 1px solid rgba(13, 115, 119, 0.14);
}
.empty-chart {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-weight: 600;
}

.complexity-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.motif-summary-cards,
.motif-summary-spacer {
  --motif-summary-row-height: 81px;
}
.motif-summary-cards .complexity-card {
  height: var(--motif-summary-row-height);
}
.motif-summary-spacer {
  display: grid;
  grid-template-rows: var(--motif-summary-row-height);
  margin-top: 16px;
}
.complexity-card {
  border-radius: 16px;
  padding: 14px 12px;
  background: #f8fafc;
  border: 1px solid rgba(203,213,225,0.72);
}
.complexity-card--accent {
  background: #f1fafa;
  border-color: rgba(13,115,119,0.22);
}
.complexity-value {
  display: block;
  color: #0D7377;
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1;
}
.complexity-label {
  display: block;
  color: #64748b;
  font-size: 0.78rem;
  margin-top: 7px;
  white-space: nowrap;
}

.species-richness-container,
.leaderboard-container {
  display: flex;
  flex-direction: column;
}
.gene-data-state { min-height: 430px; }
.species-richness-row,
.leaderboard-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(226,232,240,0.78);
}
.species-richness-row:last-child,
.leaderboard-row:last-child { border-bottom: none; }
.species-name-col { min-width: 168px; }
.species-common { font-weight: 700; color: #1e293b; font-size: 0.9rem; }
.species-latin { color: #94a3b8; font-size: 0.78rem; font-style: italic; }
.species-leader-name {
  min-width: 146px;
  max-width: 146px;
  overflow: hidden;
}
.species-leader-name .species-common,
.species-leader-name .species-latin {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.species-bar-col { flex: 1; display: flex; align-items: center; gap: 12px; min-width: 0; }
.species-bar-track,
.leaderboard-bar-track {
  flex: 1;
  height: 10px;
  background: rgba(226,232,240,0.74);
  border-radius: 999px;
  overflow: hidden;
}
.species-bar-fill,
.leaderboard-bar-fill {
  height: 100%;
  border-radius: 999px;
  transform-origin: left center;
  animation: barGrow 900ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes barGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.species-bar-count { min-width: 86px; text-align: right; color: #0D7377; font-weight: 700; font-size: 0.84rem; }
.assembly-chip { min-width: 54px; justify-content: center; }

.leaderboard-header { align-items: flex-start; }
.rank-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.rank-gold { background: linear-gradient(135deg, #D9A441, #A96F4C); color: white; }
.rank-silver { background: linear-gradient(135deg, #94a3b8, #64748b); color: white; }
.rank-bronze { background: linear-gradient(135deg, #B7791F, #8A5A22); color: white; }
.rank-default { background: rgba(226,232,240,0.9); color: #64748b; }
.gene-name-link { min-width: 100px; color: #0D7377; font-weight: 700; text-decoration: none; }
.gene-name-link:hover { text-decoration: underline; }
.gene-species-chip {
  min-width: 120px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}
.leaderboard-bar-fill { background: linear-gradient(90deg, #0D7377, #14919B); }
.species-leader-bar-fill { background: linear-gradient(90deg, #355C7D, #4A7898); }

@media (max-width: 1024px) {
  .hero-content {
    padding-left: 22px !important;
    padding-right: 22px !important;
  }

  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stats-card-row { grid-template-columns: 1fr; }
  .hero-orbit { opacity: 0.28; }
  .flow-grid { grid-template-columns: 1fr; }
  .flow-connector { min-height: 46px; }
  .flow-connector::before { left: 50%; right: auto; top: 0; bottom: 0; border-top: none; border-left: 1px dashed rgba(13,115,119,0.26); }
  .section-card { padding: 22px; }
}

@media (max-width: 640px) {
  .hero-section {
    min-height: 240px;
  }

  .hero-content {
    padding: 36px 18px 42px;
  }

  .hero-content :deep(.text-h3) {
    font-size: 2rem !important;
    line-height: 1.15;
  }

  .hero-content :deep(.text-h6) {
    font-size: 1rem !important;
  }

  .stats-hero,
  .stats-hero-container { min-height: 300px; }
  .stats-title { font-size: 2.25rem; }
  .stats-subtitle { font-size: 1.05rem; }
  .metric-grid,
  .complexity-cards { grid-template-columns: 1fr; }
  .motif-summary-spacer {
    grid-template-rows: repeat(3, var(--motif-summary-row-height));
    gap: 10px;
  }
  .species-richness-row,
  .leaderboard-row { align-items: stretch; flex-direction: column; gap: 8px; }
  .species-name-col,
  .gene-species-chip,
  .species-leader-name { min-width: 0; max-width: none; }
  .species-bar-count { text-align: left; }
  .leaderboard-bar-track { width: 100%; }
  .stats-content { padding-top: 28px; }
  .section-card { padding: 18px; border-radius: 18px; }
  .stats-filter-topline {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
  .species-filter-trigger {
    max-width: 100%;
  }
  .chart-shell,
  .chart-shell--large,
  .chart-shell--wide {
    height: 300px;
  }
  .flow-node { min-height: 104px; }
  .flow-node-value { font-size: 1.65rem; }
}
</style>
