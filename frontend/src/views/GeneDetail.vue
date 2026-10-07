<template>
  <div class="gene-detail-page">
    <v-container class="py-8">
      <v-btn 
        variant="text" 
        @click="$router.back()" 
        class="mb-4"
      >
        <v-icon start>mdi-arrow-left</v-icon>
        Back to Search
      </v-btn>
      
      <div v-if="loading" class="d-flex justify-center align-center" style="min-height: 400px;">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      </div>
      
      <div v-else-if="error">
        <v-alert type="error" variant="tonal">
          {{ error }}
        </v-alert>
      </div>
      
      <div v-else-if="geneData">
        <div class="dense-view-note">
          Transcript tables and isoform diagrams can be scrolled horizontally on small screens. Desktop or tablet view is recommended for detailed comparison.
        </div>

        <!-- ── Gene header card ─────────────────────────────────── -->
        <div class="gene-header-card mb-6">
          <div class="gene-header-title">
            <v-icon icon="mdi-dna" size="22" class="mr-2" style="color: #0D7377; opacity: 0.85;"></v-icon>
            <span class="gene-name-text">{{ geneData.gene_name }}</span>
            <router-link
              :to="{ name: 'CrossSpecies', query: { gene_db_id: geneData.id } }"
              class="gene-compare-action"
            >
              <v-icon icon="mdi-vector-link" size="17"></v-icon>
              Compare orthologs
            </router-link>
          </div>
          <div class="gene-meta-row">
            <div class="gene-meta-item gene-meta-item--centered">
              <span class="gene-meta-label">Chromosome</span>
              <v-chip size="small" variant="tonal" color="primary" class="gene-meta-chip">{{ geneData.chromosome }}</v-chip>
            </div>
            <div class="gene-meta-item gene-meta-item--centered">
              <span class="gene-meta-label">Strand</span>
              <v-chip size="small" variant="tonal" color="secondary" class="gene-meta-chip">{{ geneData.strand }}</v-chip>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">Total Transcripts</span>
              <span class="gene-meta-value gene-meta-accent">{{ geneData.transcripts.length }}</span>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">PA Sites</span>
              <span class="gene-meta-value gene-meta-accent">{{ totalAPASites }}</span>
            </div>
            <div class="gene-meta-item" style="align-items: flex-start;" v-if="speciesInfo">
              <span class="gene-meta-label">Species</span>
              <span class="gene-meta-value">
                {{ formatSpeciesName(speciesInfo) }}
                <span v-if="formatSpeciesSubtitle(speciesInfo)" style="font-style: italic; opacity: 0.65; font-size: 13.5px;">{{ formatSpeciesSubtitle(speciesInfo) }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- ── Gene Summary (MyGene.info) ───────────────────────── -->
        <div class="section-card mb-6">
          <div class="section-title">
            <v-icon size="18" class="mr-2" style="color: #0D7377;">mdi-text-box-outline</v-icon>
            Gene Summary
          </div>

          <div class="panel-box">
            <!-- Panel header -->
            <div class="panel-header">
              <div class="panel-header-left">
                <span class="panel-icon-wrap panel-icon-teal">
                  <v-icon size="18" color="white">mdi-dna</v-icon>
                </span>
                <div>
                  <div class="panel-title-text">{{ geneSummaryData?.symbol || geneData.gene_name }}</div>
                  <div class="panel-subtitle-text">
                    {{ geneSummaryData?.fullName || 'Gene information from NCBI / MyGene.info' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Panel body -->
            <div class="panel-body">

              <!-- Loading -->
              <div v-if="geneSummaryLoading" class="d-flex align-center py-4">
                <v-progress-circular indeterminate color="primary" size="22" width="2" class="mr-3"></v-progress-circular>
                <span class="text-caption text-medium-emphasis">Fetching gene information…</span>
              </div>

              <!-- Error -->
              <v-alert v-else-if="geneSummaryError" type="warning" variant="tonal" density="compact" class="text-caption">
                Gene summary not available for this gene.
              </v-alert>

              <!-- No hit -->
              <div v-else-if="!geneSummaryData" class="text-caption text-medium-emphasis py-2">
                No gene summary found.
              </div>

              <!-- Data — NCBI-style definition list -->
              <template v-else>
                <div class="gs-scroll-frame">
                <dl class="gs-deflist">

                  <!-- Also known as -->
                  <div v-if="geneSummaryData.aliases?.length" class="gs-row">
                    <dt class="gs-dt">Also known as</dt>
                    <dd class="gs-dd">{{ geneSummaryData.aliases.join('; ') }}</dd>
                  </div>

                  <!-- Gene type -->
                  <div v-if="geneSummaryData.geneType" class="gs-row">
                    <dt class="gs-dt">Gene type</dt>
                    <dd class="gs-dd">{{ geneSummaryData.geneType.replace(/-/g, ' ') }}</dd>
                  </div>

                   <!-- See related — smart Ensembl / RefSeq / UniProt / NCBI links -->
                   <div class="gs-row">
                     <dt class="gs-dt">See related</dt>
                      <dd class="gs-dd gs-related-dd">
                        <span v-if="geneSummaryData.ensemblGene || geneData.gene_id?.startsWith('ENS')" class="gs-id-entry">
                          <span class="gs-id-source">Ensembl</span>
                          <a :href="`https://www.ensembl.org/id/${geneSummaryData.ensemblGene || geneData.gene_id}`" target="_blank" class="gs-id-code gs-id-href">{{ geneSummaryData.ensemblGene || geneData.gene_id }}</a>
                        </span>
                        <span v-if="geneSummaryData.refseqMrna" class="gs-id-entry">
                          <span class="gs-id-source">RefSeq</span>
                          <a :href="`https://www.ncbi.nlm.nih.gov/nuccore/${geneSummaryData.refseqMrna}`" target="_blank" class="gs-id-code gs-id-href">{{ geneSummaryData.refseqMrna }}</a>
                        </span>
                        <span v-if="geneSummaryData.uniprot" class="gs-id-entry">
                          <span class="gs-id-source">UniProtKB</span>
                          <a :href="`https://www.uniprot.org/uniprot/${geneSummaryData.uniprot}`" target="_blank" class="gs-id-code gs-id-href">{{ geneSummaryData.uniprot }}</a>
                        </span>
                        <span v-if="geneSummaryData.entrezgene" class="gs-id-entry">
                          <span class="gs-id-source">NCBI Gene</span>
                          <a :href="`https://www.ncbi.nlm.nih.gov/gene/${geneSummaryData.entrezgene}`" target="_blank" class="gs-id-code gs-id-href">{{ geneSummaryData.entrezgene }}</a>
                        </span>
                      </dd>
                   </div>

                  <!-- Summary text -->
                  <div class="gs-row">
                    <dt class="gs-dt">Summary</dt>
                    <dd class="gs-dd">
                      <p v-if="geneSummaryData.summary" class="gs-summary-text">{{ geneSummaryData.summary }}</p>
                      <p v-else class="gs-summary-text gs-summary-empty">No functional summary available from NCBI Gene.</p>
                    </dd>
                  </div>

                  <!-- KEGG Pathways — bottom -->
                  <div v-if="geneSummaryData.pathways?.length" class="gs-row">
                    <dt class="gs-dt">KEGG Pathways</dt>
                    <dd class="gs-dd">
                      <div class="gs-chip-row">
                        <span
                          v-for="pw in (showAllPathways ? geneSummaryData.pathways : geneSummaryData.pathways.slice(0, 10))"
                          :key="pw.id"
                          class="gs-chip gs-chip-pathway"
                        >{{ pw.name }}</span>
                        <button
                          v-if="geneSummaryData.pathways.length > 10"
                          class="gs-chip gs-chip-more"
                          @click="showAllPathways = !showAllPathways"
                        >
                          {{ showAllPathways ? '− show less' : `+${geneSummaryData.pathways.length - 10} more` }}
                        </button>
                      </div>
                    </dd>
                  </div>

                </dl>
                </div>
              </template>
            </div>
          </div>
        </div>

        <!-- ── Transcripts and APA Sites ────────────────────────── -->
        <div class="section-card">

          <!-- Section title -->
          <div class="section-title">
            <v-icon size="18" class="mr-2" style="color: #0D7377;">mdi-source-branch</v-icon>
            Transcripts and PA Sites
          </div>

          <!-- ── Panel 1: Transcript Details ──────────────────── -->
          <div class="panel-box mb-5">
            <div class="panel-header">
              <div class="panel-header-left">
                <span class="panel-icon-wrap panel-icon-teal">
                  <v-icon size="18" color="white">mdi-table</v-icon>
                </span>
                <div>
                  <div class="panel-title-text">Transcript Details</div>
                  <div class="panel-subtitle-text">PA sites and sample coverage per transcript isoform</div>
                </div>
              </div>
            </div>

            <!-- Table -->
            <div class="tx-table-container">
              <table class="tx-table">
                <colgroup>
                  <col class="tx-col-expand">
                  <col class="tx-col-transcript">
                  <col class="tx-col-biotype">
                  <col class="tx-col-sites">
                  <col class="tx-col-samples">
                  <col class="tx-col-dominant">
                </colgroup>
                 <thead>
                   <tr>
                     <th class="tx-th tx-th-sticky tx-th-expand"></th>
                     <th class="tx-th tx-th-sticky">Transcript</th>
                     <th class="tx-th tx-th-sticky">Biotype</th>
                     <th class="tx-th tx-th-sticky tx-th-center">PA Sites</th>
                     <th class="tx-th tx-th-sticky tx-th-center">Samples</th>
                     <th class="tx-th tx-th-sticky tx-th-dominant">Dominant PA Site</th>
                   </tr>
                 </thead>
                <tbody>
                  <template v-for="tx in geneData.transcripts" :key="tx.transcript_id">
                    <tr
                       class="tx-row"
                       :class="{ 'tx-row-expanded': expandedTxIds.includes(tx.transcript_id) }"
                       @click="toggleExpand(tx.transcript_id)"
                      style="cursor: pointer;"
                    >
                      <!-- Expand Chevron -->
                      <td class="tx-td tx-chevron-cell">
                         <v-icon size="20" class="tx-chevron" :class="{ 'tx-chevron-open': expandedTxIds.includes(tx.transcript_id) }">mdi-chevron-right</v-icon>
                      </td>

                      <!-- Transcript ID -->
                      <td class="tx-td">
                        <div class="tx-id-stack">
                          <router-link
                            :to="{ name: 'LocusDetail', params: { transcriptId: tx.transcript_id }, query: { species: geneData.species } }"
                            class="tx-id-link"
                            @click.stop
                          >{{ tx.transcript_id }}</router-link>
                          <span
                            v-if="transcriptRepresentativeStatus(tx)"
                            class="tx-representative-badge"
                            :class="representativeStatusClass(transcriptRepresentativeStatus(tx))"
                            title="Reference representative transcript"
                          >
                            {{ formatRepresentativeStatus(transcriptRepresentativeStatus(tx)) }}
                          </span>
                        </div>
                      </td>

                       <!-- Biotype Badge -->
                       <td class="tx-td">
                         <span class="tx-biotype-badge" :class="getBiotypeClass(tx.apa_sites[0]?.transcript_biotype)">
                           {{ formatBiotype(tx.apa_sites[0]?.transcript_biotype) }}
                         </span>
                       </td>

                       <!-- PA site count -->
                       <td class="tx-td" style="text-align: center; white-space: nowrap;">
                         <span class="tx-count-badge">{{ tx.apa_site_count }}</span>
                       </td>

                       <!-- Sample coverage count -->
                       <td class="tx-td" style="text-align: center; white-space: nowrap;">
                         <div class="tx-sample-count" v-if="tx.samples?.length">
                           <v-icon size="14" class="mr-1">mdi-flask</v-icon>
                           {{ tx.samples.length }} sample{{ tx.samples.length !== 1 ? 's' : '' }}
                         </div>
                         <span class="tx-no-samples" v-else>-</span>
                       </td>

                      <!-- Dominant PA site -->
                       <td class="tx-td tx-td-dominant">
                         <span class="tx-dominant-site-tag" v-if="dominantSite(tx)" :title="dominantSite(tx)?.unified_id">
                           <v-icon size="12" class="mr-1" color="amber-darken-2">mdi-star</v-icon>
                           <span class="tx-dominant-site-id">{{ dominantSite(tx)?.unified_id }}</span>
                         </span>
                         <span v-else class="tx-no-samples">-</span>
                       </td>
                    </tr>
                    
                    <!-- Expanded row -->
                     <tr v-if="expandedTxIds.includes(tx.transcript_id)" class="tx-expanded-row-container">
                      <td colspan="6" class="tx-expanded-td">
                        <Transition name="tx-expand" appear>
                          <div class="tx-expanded-content">
                            <table class="tx-inner-table">
                 <colgroup>
                                  <col class="tx-inner-col-spacer">
                                  <col class="tx-inner-col-site">
                                  <col class="tx-inner-col-cluster">
                                  <col class="tx-inner-col-abundance">
                                  <col class="tx-inner-col-pa-level">
                                  <col class="tx-inner-col-samples">
                                </colgroup>
                               <thead>
                                 <tr>
                                    <th class="tx-inner-th tx-inner-th-spacer" aria-hidden="true"></th>
                                    <th class="tx-inner-th tx-inner-th-site">Site ID</th>
                                    <th class="tx-inner-th tx-inner-th-cluster">
                                      <div class="tx-inner-th-row">
                                        Cluster Range
                                        <v-menu location="bottom end" :close-on-content-click="true" max-width="355">
                                          <template #activator="{ props }">
                                            <v-icon
                                              v-bind="props"
                                              size="13"
                                              class="tx-info-icon"
                                              @click.stop
                                            >mdi-help-circle-outline</v-icon>
                                          </template>
                                          <v-card class="tx-info-popover" elevation="0" rounded="lg">
                                            <v-card-text class="tx-info-popover-text">
                                              Genomic start and end coordinates of the PA cluster. This range groups nearby cleavage positions that represent the same polyadenylation event.
                                            </v-card-text>
                                          </v-card>
                                        </v-menu>
                                      </div>
                                    </th>
                                    <th class="tx-inner-th tx-inner-th-abundance">
                                      <div class="tx-inner-th-row">
                                        Mean Abundance
                                        <v-menu location="bottom end" :close-on-content-click="true" max-width="320">
                                          <template #activator="{ props }">
                                            <v-icon
                                              v-bind="props"
                                              size="13"
                                              class="tx-info-icon"
                                              @click.stop
                                            >mdi-help-circle-outline</v-icon>
                                          </template>
                                          <v-card class="tx-info-popover" elevation="0" rounded="lg">
                                            <v-card-text class="tx-info-popover-text">
                                              Arithmetic mean of the relative polyadenylation usage of this PA site on this transcript across all samples in which it was detected.
                                            </v-card-text>
                                          </v-card>
                                        </v-menu>
                                      </div>
                                    </th>
                                    <th class="tx-inner-th tx-inner-th-pa-level">PAS Level</th>
                                    <th class="tx-inner-th tx-inner-th-samples">Samples</th>
                                 </tr>
                               </thead>
                              <tbody>
                                <tr v-for="site in tx.apa_sites" :key="site.unified_id" class="tx-inner-row">
                                    <td class="tx-inner-td tx-inner-td-spacer" aria-hidden="true"></td>
                                    <td class="tx-inner-td tx-inner-td-site">
                                      <span class="tx-site-id-tag" :title="site.unified_id">{{ site.unified_id }}</span>
                                    </td>
                                   <td class="tx-inner-td tx-inner-td-cluster">
                                      <span class="tx-cluster-range-tag">{{ formatClusterRange(site) }}</span>
                                    </td>
                                   <td class="tx-inner-td tx-inner-td-abundance">
                                    <div class="tx-abundance-wrapper">
                                      <div class="tx-abundance-bar">
                                        <div class="tx-abundance-fill" :style="{ width: abundanceBarWidth(site, tx) }"></div>
                                      </div>
                                      <span class="tx-abundance-val">{{ (meanSiteAbundance(site) * 100).toFixed(1) }}%</span>
                                    </div>
                                  </td>
                                  <td class="tx-inner-td tx-inner-td-pa-level">
                                    <span class="tx-pa-level-pill">{{ formatPaLevel(site.pa_level) }}</span>
                                  </td>
                                   <td class="tx-inner-td tx-inner-td-samples">
                                     <div class="tx-sample-chips">
                                       <span
                                         v-for="s in visibleSamples(site, tx)"
                                         :key="s.sample_name"
                                         class="tx-sample-pill"
                                       >{{ formatSampleName(s.sample_name) }}</span>
                                         <button
                                           v-if="dedupedSampleCount(site) > 4 && !isSampleExpanded(site, tx)"
                                           class="tx-sample-more-btn"
                                           @click.stop="toggleSampleExpand(site, tx)"
                                         >+{{ hiddenSampleCount(site, tx) }} more</button>
                                         <button
                                           v-if="dedupedSampleCount(site) > 4 && isSampleExpanded(site, tx)"
                                           class="tx-sample-more-btn tx-sample-more-btn--collapse"
                                           @click.stop="toggleSampleExpand(site, tx)"
                                         >− show less</button>
                                     </div>
                                   </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </Transition>
                      </td>
                    </tr>
                  </template>
                  <tr v-if="geneData.transcripts.length === 0">
                    <td colspan="6" class="tx-empty">No transcripts found</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- ── Panel 2: Isoform–APA Fingerprint ─────────────── -->
          <div class="panel-box mb-5">
            <div class="panel-header">
              <div class="panel-header-left">
                <span class="panel-icon-wrap panel-icon-teal">
                  <v-icon size="18" color="white">mdi-fingerprint</v-icon>
                </span>
                <div>
                  <div class="panel-title-text">Isoform–APA Fingerprint</div>
                  <div class="panel-subtitle-text" style="white-space: nowrap;">Genome-aligned PA sites per isoform, coloured by Shared / Private classification</div>
                </div>
              </div>
            </div>
            <div class="panel-body">
              <div v-if="structuresLoading" class="d-flex justify-center align-center py-8">
                <v-progress-circular indeterminate color="primary" size="40"></v-progress-circular>
                <span class="ml-3 text-caption text-grey">Loading transcript structures…</span>
              </div>
              <MultiIsoformBrowser
                v-else
                :geneData="geneData"
                :transcriptStructures="transcriptStructures"
              />
            </div>
          </div>

        </div>
      </div>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiService } from '@/services/api'
import { formatSampleName, formatSpeciesName, formatSpeciesSubtitle } from '@/utils/formatters'
import MultiIsoformBrowser from '@/components/MultiIsoformBrowser.vue'

const route = useRoute()

const loading = ref(true)
const structuresLoading = ref(true)
const error = ref(null)
const geneData = ref(null)
const transcriptStructures = ref({})
const speciesInfo = ref(null)

// ── Gene summary (MyGene.info) ─────────────────────────────────────────────
const geneSummaryLoading = ref(false)
const geneSummaryError = ref(null)
const geneSummaryData = ref(null)
const showAllPathways = ref(false)

const fetchGeneSummary = async (geneId, speciesName) => {
  geneSummaryLoading.value = true
  geneSummaryError.value = null
  try {
    const summary = await apiService.getGeneSummary(geneId, speciesName)
    if (!summary?.summary && !summary?.fullName) {
      geneSummaryData.value = null
      return
    }
    geneSummaryData.value = {
      symbol:      summary.symbol      ?? null,
      fullName:    summary.fullName    ?? null,
      aliases:     summary.aliases     ?? [],
      geneType:    summary.geneType    ?? null,
      summary:     summary.summary     ?? null,
      pathways:    summary.pathways    ?? [],
      entrezgene:  summary.entrezgene  ?? null,
      uniprot:     summary.uniprot     ?? null,
      hgnc:        summary.hgnc        ?? null,
      refseqMrna:  summary.refseqMrna  ?? null,
      ensemblGene: summary.ensemblGene ?? null,
    }
  } catch (err) {
    console.warn('Gene summary fetch failed:', err)
    geneSummaryError.value = 'fetch_failed'
  } finally {
    geneSummaryLoading.value = false
  }
}

const totalAPASites = computed(() => {
  if (!geneData.value) return 0
  const ids = new Set()
  for (const t of geneData.value.transcripts) {
    for (const s of t.apa_sites) ids.add(s.unified_id)
  }
  return ids.size
})

// Reactive arrays — Vue 3 tracks .push(), .splice(), .includes() reliably
const expandedTxIds = ref([])

const toggleExpand = (txId) => {
  const idx = expandedTxIds.value.indexOf(txId)
  if (idx >= 0) {
    expandedTxIds.value.splice(idx, 1)
  } else {
    expandedTxIds.value.push(txId)
  }
}

const expandedSampleSites = ref([])

const sampleExpansionKey = (site, tx) =>
  `${tx?.transcript_id ?? 'unknown'}::${site?.unified_id ?? 'unknown'}`

const isSampleExpanded = (site, tx) =>
  expandedSampleSites.value.includes(sampleExpansionKey(site, tx))

const toggleSampleExpand = (site, tx) => {
  const key = sampleExpansionKey(site, tx)
  const idx = expandedSampleSites.value.indexOf(key)
  if (idx >= 0) {
    expandedSampleSites.value.splice(idx, 1)
  } else {
    expandedSampleSites.value.push(key)
  }
}

const visibleSamples = (site, tx) => {
  const details = dedupeSampleDetails(site.sample_details || [])
  if (isSampleExpanded(site, tx)) return details
  return details.slice(0, 4)
}

const hiddenSampleCount = (site, tx) =>
  Math.max(0, dedupeSampleDetails(site.sample_details || []).length - visibleSamples(site, tx).length)

const dedupedSampleCount = (site) => dedupeSampleDetails(site.sample_details || []).length

const dedupeSampleDetails = (details) => {
  const seen = new Set()
  return details.filter(detail => {
    const key = formatSampleName(detail.sample_name).toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const formatClusterRange = (site) => {
  if (site.cluster_start == null || site.cluster_end == null) return '—'
  return `${site.cluster_start}:${site.cluster_end}`
}

const formatPaLevel = (level) => {
  const value = String(level || '').trim()
  return value || '—'
}

const representativePriority = {
  MANE_Select: 1,
  RefSeq_Select: 2,
  Ensembl_Canonical: 3,
  APPRIS_Principal: 4
}

const transcriptRepresentativeStatus = (tx) => {
  const statuses = (tx.apa_sites || [])
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

const representativeStatusClass = (status) => {
  return {
    MANE_Select: 'tx-representative-badge--mane',
    RefSeq_Select: 'tx-representative-badge--refseq',
    Ensembl_Canonical: 'tx-representative-badge--ensembl',
    APPRIS_Principal: 'tx-representative-badge--appris'
  }[status] || 'tx-representative-badge--default'
}



const dominantSite = (tx) => {
  if (!tx.apa_sites || tx.apa_sites.length === 0) return null
  return tx.apa_sites.reduce((prev, current) =>
    (prev.sample_details?.length ?? 0) >= (current.sample_details?.length ?? 0) ? prev : current
  )
}

const meanSiteAbundance = (site) => {
  if (!site.sample_details || site.sample_details.length === 0) return 0
  const sum = site.sample_details.reduce((acc, s) => acc + (s.site_abundance ?? 0), 0)
  return sum / site.sample_details.length
}

const maxTxAbundance = (tx) => {
  if (!tx.apa_sites || tx.apa_sites.length === 0) return 1
  const max = Math.max(...tx.apa_sites.map(s => meanSiteAbundance(s)))
  return max > 0 ? max : 1
}

const abundanceBarWidth = (site, tx) => {
  const ratio = meanSiteAbundance(site) / maxTxAbundance(tx)
  const bounded = Math.min(1, Math.max(0, ratio || 0))
  return `${bounded * 100}%`
}

const formatBiotype = (biotype) => {
  if (!biotype) return 'unknown'
  if (biotype === 'protein_coding') return 'mRNA'
  if (biotype === 'lncRNA' || biotype === 'lnc_RNA' || biotype === 'lncrna') return 'lncRNA'
  // General fallback: replace underscores with spaces, keep original casing
  return biotype.replace(/_/g, ' ')
}

const getBiotypeClass = (biotype) => {
  if (!biotype) return 'tx-biotype-grey'
  if (biotype === 'protein_coding') return 'tx-biotype-teal'
  if (biotype === 'lncRNA' || biotype === 'lnc_RNA' || biotype === 'lncrna' || biotype === 'processed_transcript') return 'tx-biotype-amber'
  return 'tx-biotype-grey'
}

onMounted(async () => {
  const geneId = route.params.geneId
  const species = route.query.species
  
  try {
    loading.value = true
    geneData.value = await apiService.getGeneDetail(geneId, species)

    // Fire gene summary fetch (non-blocking)
    fetchGeneSummary(geneId, geneData.value.species)

    // Fetch species info from first transcript's locus detail (non-fatal)
    if (geneData.value?.transcripts?.length) {
      try {
        const firstTx = await apiService.getLocusDetail(
          geneData.value.transcripts[0].transcript_id,
          geneData.value.species
        )
        speciesInfo.value = firstTx?.apa_sites?.[0]?.species ?? null
      } catch {
        // Non-fatal — species badge is optional
      }
    }
  } catch (err) {
    console.error('Failed to load gene detail:', err)
    error.value = 'Failed to load gene details. Please try again.'
  } finally {
    loading.value = false
  }

  if (geneData.value?.transcripts?.length) {
    try {
      structuresLoading.value = true
      const entries = await Promise.all(
        geneData.value.transcripts.map(tx =>
          apiService.getTranscriptStructure(tx.transcript_id, geneData.value.species)
            .then(s => [tx.transcript_id, s])
            .catch(() => [tx.transcript_id, null])
        )
      )
      transcriptStructures.value = Object.fromEntries(
        entries.filter(([, s]) => s !== null)
      )
    } finally {
      structuresLoading.value = false
    }
  } else {
    structuresLoading.value = false
  }
})
</script>

<style scoped>
.gene-detail-page {
  min-height: 100vh;
  background: rgb(var(--v-theme-background));
}

a { text-decoration: none; }
a:hover { text-decoration: underline; }

code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* ── Gene header card ────────────────────────────────────────────── */
.gene-header-card {
  background: rgba(255, 255, 255, 0.88) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid rgba(203, 213, 225, 0.72) !important;
  border-radius: 16px;
  padding: 20px 24px;
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.055) !important;
}

.gene-header-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.gene-compare-action {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
  padding: 7px 11px;
  border: 1px solid rgba(13, 115, 119, 0.18);
  border-radius: 9px;
  background: #effafa;
  color: #0d7377;
  font-size: 0.8rem;
  font-weight: 700;
  text-decoration: none !important;
}

.gene-compare-action:hover {
  border-color: rgba(13, 115, 119, 0.34);
  background: #e4f6f5;
  color: #0a5c5f;
}

.gene-name-text {
  font-size: 1.6rem;
  font-weight: 700;
  color: rgba(0,0,0,0.87);
  letter-spacing: -0.01em;
}

.gene-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 28px;
}

.gene-meta-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.gene-meta-item--centered {
  align-items: center;
}

.gene-meta-label {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(0,0,0,0.42);
}

.gene-meta-value {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0,0,0,0.80);
  display: flex;
  align-items: center;
  gap: 4px;
}

.gene-meta-accent {
  font-size: 14px;
  font-weight: 700;
  color: #0D7377;
}

.gene-meta-chip :deep(.v-chip__content) {
  font-size: 13.5px;
  font-weight: 500;
}

/* ── Outer section card ──────────────────────────────────────────── */
.section-card {
  background: rgba(255, 255, 255, 0.88) !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  border: 1px solid rgba(203, 213, 225, 0.72) !important;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.055) !important;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 1.15rem;
  font-weight: 700;
  color: rgba(0,0,0,0.80);
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(0,0,0,0.07);
}

/* ── Panel box (each of the 3 sections) ─────────────────────────── */
.panel-box {
  border: 1px solid rgba(13, 115, 119, 0.14);
  border-radius: 12px;
  overflow: hidden;
  background: #f8fbfb !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
}

/* ── Unified panel header ────────────────────────────────────────── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  background: #f1f8f8;
  border-bottom: 1px solid rgba(13, 115, 119, 0.12);
  flex-wrap: wrap;
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Coloured icon pill */
.panel-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  flex-shrink: 0;
}

.panel-icon-teal {
  background: #0D7377;
}

.panel-title-text {
  font-size: 14.5px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.87);
  line-height: 1.3;
  font-family: 'IBM Plex Sans', sans-serif;
}

.panel-subtitle-text {
  font-size: 13.5px;
  color: rgba(0, 0, 0, 0.60);
  margin-top: 2px;
  max-width: 480px;
  font-family: 'IBM Plex Sans', sans-serif;
}

/* Panel body padding for browser/coupling */
.panel-body {
  padding: 16px;
}

/* ── Transcript table ────────────────────────────────────────────── */
.tx-table-container {
  overflow-x: auto;
  max-height: 600px;
}

.tx-table {
  width: 100%;
  min-width: 860px;
  table-layout: fixed;
  border-collapse: collapse;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 14.5px;
}

.tx-col-expand {
  width: 5%;
}

.tx-col-transcript {
  width: 26%;
}

.tx-col-biotype {
  width: 13%;
}

.tx-col-sites {
  width: 11%;
}

.tx-col-samples {
  width: 15%;
}

.tx-col-dominant {
  width: 30%;
}

.tx-th-sticky {
  position: sticky;
  top: 0;
  z-index: 2;
}

.tx-th {
  padding: 9px 16px;
  text-align: left;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.4px !important;
  text-transform: uppercase !important;
  color: #475569 !important;
  background: #f1f8f8 !important;
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(13, 115, 119, 0.10);
  white-space: nowrap;
  font-family: 'IBM Plex Sans', sans-serif !important;
}

.tx-th-expand,
.tx-th-center {
  text-align: center;
}

.tx-th-dominant {
  padding-left: 24px;
}

.tx-row {
  border-bottom: 1px solid rgba(0, 0, 0, 0.055);
  transition: background 0.12s ease;
}

.tx-row:hover, .tx-row-expanded {
  background: #f3fafa;
}

.tx-row:last-child {
  border-bottom: none;
}

.tx-td {
  padding: 11px 16px;
  vertical-align: middle;
  color: rgba(0, 0, 0, 0.82);
}

.tx-td-dominant {
  padding-left: 24px;
}

.tx-chevron-cell {
  text-align: center;
  padding: 11px 8px;
}

.tx-chevron {
  color: rgba(0, 0, 0, 0.38);
  transition: transform 0.2s ease, color 0.2s ease;
}

.tx-row:hover .tx-chevron {
  color: #0D7377;
}

.tx-chevron-open {
  transform: rotate(90deg);
  color: #0D7377;
}

.tx-id-link {
  font-weight: 600;
  font-size: 14.5px;
  color: #0D7377;
  text-decoration: none;
  font-family: 'IBM Plex Sans', sans-serif;
  display: inline-flex;
  align-items: center;
}

.tx-id-stack {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.tx-representative-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  padding: 1px 6px;
  border-radius: 999px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 9.5px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: 0.02em;
  white-space: nowrap;
  border: 1px solid rgba(100, 116, 139, 0.22);
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
}

.tx-representative-badge--mane {
  color: #0f766e;
  background: rgba(240, 253, 250, 0.88);
  border-color: rgba(13, 148, 136, 0.22);
}

.tx-representative-badge--refseq {
  color: #355c7d;
  background: rgba(241, 245, 249, 0.95);
  border-color: rgba(53, 92, 125, 0.22);
}

.tx-representative-badge--ensembl {
  color: #3f6f56;
  background: rgba(242, 248, 244, 0.92);
  border-color: rgba(63, 111, 86, 0.22);
}

.tx-representative-badge--appris {
  color: #9a5b13;
  background: rgba(255, 251, 235, 0.9);
  border-color: rgba(194, 120, 25, 0.24);
}

.tx-id-link:hover {
  color: #14919B;
  text-decoration: underline;
}

.tx-biotype-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.tx-biotype-teal {
  background: rgba(13, 115, 119, 0.1);
  color: #0D7377;
  border: 1px solid rgba(13, 115, 119, 0.2);
}

.tx-biotype-amber {
  background: rgba(255, 152, 0, 0.1);
  color: #f57c00;
  border: 1px solid rgba(255, 152, 0, 0.2);
}

.tx-biotype-grey {
  background: rgba(0, 0, 0, 0.06);
  color: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.tx-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  background: rgba(13, 115, 119, 0.12);
  color: #0D7377;
  border: 1px solid rgba(13, 115, 119, 0.25);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 700;
  font-family: 'IBM Plex Sans', sans-serif;
}

.tx-sample-count {
  font-size: 13px;
  color: rgba(0, 0, 0, 0.65);
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.tx-no-samples {
  color: rgba(0, 0, 0, 0.3);
  font-size: 13px;
}

.tx-sample-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  align-content: center;
  gap: 7px;
  overflow: visible;
  max-width: 100%;
  min-width: 0;
  line-height: 1.35;
}

.tx-site-id-tag,
.tx-cluster-range-tag,
.tx-pa-level-pill,
.tx-sample-pill {
  display: inline-flex;
  align-items: center;
  height: 25px;
  padding: 4px 9px;
  border-radius: 10px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 11.5px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  max-width: 100%;
}

.tx-sample-pill {
  background: rgba(255, 255, 255, 0.72);
  color: rgba(15, 46, 48, 0.78);
  border: 1px solid rgba(13, 115, 119, 0.16);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.tx-pos-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tx-pos-tag {
  display: inline-flex;
  align-items: center;
  background: rgba(13, 115, 119, 0.06);
  color: rgba(0, 0, 0, 0.70);
  border: 1px solid rgba(13, 115, 119, 0.15);
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 500;
  padding: 2px 8px;
  white-space: nowrap;
  cursor: default;
}

.tx-pos-tag-inner {
  font-size: 12px;
}

/* Dominant PA site tag in primary row */
.tx-dominant-site-tag {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  gap: 4px;
}

.tx-dominant-site-id {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 14.5px;
  font-weight: 600;
  color: #0D7377;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
}

/* Site ID tag in inner table */
.tx-site-id-tag {
  color: #0D7377;
  background: rgba(13, 115, 119, 0.10);
  border: 1px solid rgba(13, 115, 119, 0.22);
  cursor: default;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tx-cluster-range-tag {
  color: rgba(15, 23, 42, 0.78);
  background: rgba(53, 92, 125, 0.08);
  border: 1px solid rgba(53, 92, 125, 0.16);
  font-family: 'IBM Plex Mono', monospace;
  min-width: max-content;
}

.tx-pa-level-pill {
  color: #0A5C5F;
  background: rgba(13, 115, 119, 0.075);
  border: 1px solid rgba(13, 115, 119, 0.16);
  font-size: 11.25px;
  letter-spacing: 0.01em;
}

/* Sample "+N more" / "show less" toggle button in inner table */
.tx-sample-more-btn {
  display: inline-flex;
  align-items: center;
  font-size: 11.5px;
  font-weight: 700;
  font-family: 'IBM Plex Sans', sans-serif;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.075);
  border: 1px solid rgba(13, 115, 119, 0.18);
  border-radius: 999px;
  padding: 3px 9px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
  line-height: 1.5;
}

.tx-sample-more-btn:hover {
  background: rgba(13, 115, 119, 0.16);
  color: #0a5c60;
}

.tx-sample-more-btn--collapse {
  background: rgba(0, 0, 0, 0.05);
  color: rgba(0, 0, 0, 0.50);
  border-color: rgba(0, 0, 0, 0.15);
}

.tx-sample-more-btn--collapse:hover {
  background: rgba(0, 0, 0, 0.09);
  color: rgba(0, 0, 0, 0.70);
}

.tx-empty {
  padding: 32px 16px;
  text-align: center;
  color: rgba(0, 0, 0, 0.38);
  font-size: 14.5px;
}

/* Expanded row */
.tx-expanded-row-container {
  background: #f6faf9;
  border-bottom: 1px solid rgba(13, 115, 119, 0.11);
}

.tx-expanded-td {
  padding: 0;
}

.tx-expanded-content {
  position: relative;
  padding: 14px 18px 18px 5%;
  overflow-x: auto;
}

.tx-expanded-content::before {
  content: none;
}

.tx-expand-enter-active, .tx-expand-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.tx-expand-enter-from, .tx-expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.tx-inner-table {
  width: 100%;
  min-width: 720px;
  table-layout: fixed;
  border-collapse: collapse;
  background: #ffffff;
  border: 1px solid rgba(13, 115, 119, 0.12);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03);
}

.tx-inner-col-spacer {
  width: 0;
}

.tx-inner-col-site {
  width: 20%;
}

.tx-inner-col-cluster {
  width: 19%;
}

.tx-inner-col-abundance {
  width: 18.5%;
}

.tx-inner-col-pa-level {
  width: 10.5%;
}

.tx-inner-col-samples {
  width: 32%;
}

.tx-inner-th {
  height: 36px;
  padding: 8px 12px;
  vertical-align: middle;
  text-align: left;
  font-size: 11px !important;
  font-weight: 700 !important;
  color: #475569 !important;
  background: #eef7f7 !important;
  border-bottom: 1px solid rgba(13, 115, 119, 0.11) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.52px !important;
}

.tx-inner-th-abundance {
  text-align: left;
  white-space: nowrap;
}

.tx-inner-th-abundance .tx-inner-th-row {
  justify-content: flex-start;
}

.tx-inner-td-abundance .tx-abundance-wrapper {
  justify-content: flex-start;
  width: 142px;
}

.tx-inner-th-spacer,
.tx-inner-td-spacer {
  padding: 0;
  background: #f6faf9 !important;
  border: 0 !important;
  box-shadow: none !important;
}

.tx-inner-th-site,
.tx-inner-th-cluster {
  padding-left: 16px;
}

.tx-inner-th-abundance,
.tx-inner-td-abundance {
  padding-left: 12px;
}

.tx-inner-th-cluster {
  white-space: nowrap;
  padding-left: 28px;
}

.tx-inner-th-samples {
  padding-left: 24px;
}

.tx-inner-th-pa-level,
.tx-inner-td-pa-level {
  text-align: left;
}

.tx-inner-th-row {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 100%;
}

.tx-info-icon {
  color: rgba(13, 115, 119, 0.55);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s ease;
  vertical-align: middle;
}

.tx-info-icon:hover {
  color: #0D7377;
}

.tx-info-popover {
  width: 320px;
  background: rgba(255, 255, 255, 0.60) !important;
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(13, 115, 119, 0.20) !important;
  box-shadow: 0 8px 32px rgba(13, 115, 119, 0.10), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
}

.tx-info-popover-text {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  line-height: 1.65;
  color: rgba(0, 0, 0, 0.78);
  padding: 14px 16px !important;
  text-align: justify;
}

.tx-inner-row {
  transition: background 0.16s ease;
}

.tx-inner-row:hover .tx-inner-td:not(.tx-inner-td-spacer) {
  background: #f8fcfc !important;
  border-color: rgba(13, 115, 119, 0.18);
  box-shadow: none;
}

.tx-inner-td {
  padding: 10px 12px;
  vertical-align: middle;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.78);
  background: #ffffff !important;
  border-top: 0;
  border-bottom: 1px solid rgba(203, 213, 225, 0.55);
  transition: background 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.tx-inner-td-site,
.tx-inner-td-cluster {
  padding-left: 16px;
}

.tx-inner-td-cluster {
  padding-left: 28px;
}

.tx-inner-td-samples {
  padding-left: 24px;
}

.tx-inner-row .tx-inner-td:nth-child(2) {
  border-left: 0;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.tx-inner-row .tx-inner-td:last-child {
  border-right: 0;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.tx-inner-row:last-child .tx-inner-td {
  border-bottom: 0;
}

.tx-abundance-wrapper {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 26px;
}

.tx-abundance-bar {
  width: 94px;
  height: 8px;
  background: rgba(15, 23, 42, 0.075);
  border-radius: 999px;
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08);
}

.tx-abundance-fill {
  height: 100%;
  background: linear-gradient(90deg, #0D7377, #35A29F);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.tx-abundance-val {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(15, 23, 42, 0.58);
  font-family: 'IBM Plex Mono', monospace;
  width: 44px;
}

/* ── Gene Summary definition list ───────────────────────────────── */
.gs-scroll-frame {
  width: 100%;
}

.gs-deflist {
  margin: 0;
  padding: 0;
  display: table;
  width: 100%;
  border-spacing: 0;
  border: 1px solid rgba(13, 115, 119, 0.10);
  border-radius: 8px;
  overflow: hidden;
}

.gs-row {
  display: table-row;
}

.gs-row:not(:last-child) .gs-dt,
.gs-row:not(:last-child) .gs-dd {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.gs-dt {
  display: table-cell;
  width: 160px;
  min-width: 130px;
  padding: 10px 14px 10px 16px;
  font-size: 14.5px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.62);
  vertical-align: top;
  white-space: nowrap;
  background: rgba(13, 115, 119, 0.04);
  border-right: 1px solid rgba(13, 115, 119, 0.10);
}

.gs-dd {
  display: table-cell;
  padding: 10px 16px;
  font-size: 12.5px;
  color: rgba(0, 0, 0, 0.80);
  vertical-align: middle;
  line-height: 1.55;
}

.gs-summary-text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.75;
  color: rgba(0, 0, 0, 0.72);
}

.gs-summary-empty {
  color: rgba(0, 0, 0, 0.38);
  font-style: italic;
}

/* "See related" inline links */
.gs-related-dd {
  display: table-cell;
  padding: 10px 16px;
  vertical-align: middle;
}

.gs-id-entry {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  margin-right: 20px;
  white-space: nowrap;
  vertical-align: middle;
}

.gs-id-source {
  font-size: 12.5px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.38);
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
  padding: 1px 5px;
  line-height: 1.4;
}

.gs-id-code {
  color: #0D7377;
  font-family: var(--aa-font-sans);
  font-size: 13.5px;
  font-weight: 600;
}

.gs-id-href {
  text-decoration: none;
}

.gs-id-href:hover {
  text-decoration: underline;
  color: #0a5c60;
}

/* KEGG pathway chips */
.gs-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gs-chip {
  font-size: 12.5px;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 12px;
  border: 1px solid transparent;
}

.gs-chip-pathway {
  background: rgba(13, 115, 119, 0.08);
  color: #0D7377;
  border-color: rgba(13, 115, 119, 0.20);
}

.gs-chip-more {
  background: rgba(0, 0, 0, 0.05);
  color: rgba(0, 0, 0, 0.55);
  border-color: rgba(0, 0, 0, 0.15);
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, color 0.15s;
}

.gs-chip-more:hover {
  background: rgba(13, 115, 119, 0.12);
  color: #0D7377;
  border-color: rgba(13, 115, 119, 0.30);
}

@media (max-width: 900px) {
  .gs-scroll-frame {
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    padding-bottom: 2px;
  }

  .gs-deflist {
    min-width: 760px;
  }

  .gene-meta-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .gene-meta-item,
  .gene-meta-item--centered {
    align-items: flex-start;
  }

  .panel-header-left {
    align-items: flex-start;
  }

  .tx-table {
    min-width: 920px;
  }

  .tx-inner-table {
    min-width: 920px;
  }

  .browser-svg-container {
    overflow-x: auto;
  }

  .genome-svg {
    min-width: 860px;
  }
}

@media (max-width: 640px) {
  .gene-detail-page :deep(.v-container) {
    padding-top: 24px !important;
  }

  .gene-header-card,
  .section-card {
    padding: 16px;
  }

  .gene-header-title {
    align-items: flex-start;
  }

  .gene-name-text {
    font-size: 1.32rem;
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .gene-meta-row {
    grid-template-columns: 1fr;
  }

  .section-title {
    align-items: flex-start;
    gap: 8px;
    font-size: 1.04rem;
    line-height: 1.3;
  }

  .panel-body {
    padding: 12px;
  }

  .panel-header {
    padding: 12px 14px;
  }
}
</style>
