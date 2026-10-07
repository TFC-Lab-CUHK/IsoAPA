<template>
  <div class="locus-detail-page">
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
      
      <div v-else-if="locusData">
        <div class="dense-view-note">
          Genome browser panels, heatmaps, and PA site tables can be scrolled horizontally on small screens. Desktop or tablet view is recommended for detailed inspection.
        </div>

        <!-- ── Transcript header card ─────────────────────────────── -->
        <div class="gene-header-card mb-6">
          <div class="gene-header-title">
            <v-icon icon="mdi-file-tree-outline" size="22" class="mr-2" style="color: #0D7377; opacity: 0.85;"></v-icon>
            <span class="gene-name-text">{{ locusData.transcript.transcript_id }}</span>
            <span
              v-if="transcriptRepresentativeStatus"
              class="transcript-representative-badge"
              :class="representativeStatusClass(transcriptRepresentativeStatus)"
              title="Reference representative transcript"
            >
              {{ formatRepresentativeStatus(transcriptRepresentativeStatus) }}
            </span>
          </div>
          <div class="gene-meta-row">
            <div class="gene-meta-item">
              <span class="gene-meta-label">Gene Symbol</span>
              <span class="gene-meta-value font-weight-medium">
                <router-link
                  :to="{ name: 'GeneDetail', params: { geneId: locusData.gene.id }, query: { species: locusData.apa_sites[0]?.species?.name } }"
                  class="gene-id-link"
                >{{ locusData.gene.gene_name }}</router-link>
              </span>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">Gene ID</span>
              <span class="gene-meta-value">
                <router-link
                  :to="{ name: 'GeneDetail', params: { geneId: locusData.gene.id }, query: { species: locusData.apa_sites[0]?.species?.name } }"
                  class="gene-id-link"
                >{{ locusData.gene.gene_id }}</router-link>
              </span>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">Chromosome</span>
              <v-chip size="small" variant="tonal" color="primary" class="gene-meta-chip">{{ locusData.gene.chromosome }}</v-chip>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">Strand</span>
              <v-chip size="small" variant="tonal" color="secondary" class="gene-meta-chip">{{ locusData.gene.strand }}</v-chip>
            </div>
            <div class="gene-meta-item">
              <span class="gene-meta-label">PA Sites</span>
              <span class="gene-meta-value gene-meta-accent">{{ locusData.apa_sites.length }}</span>
            </div>
            <div class="gene-meta-item" v-if="displayBiotype">
              <span class="gene-meta-label">Biotype</span>
              <span class="gene-meta-value">
                <v-chip size="small" variant="tonal" color="teal" class="gene-meta-chip">{{ displayBiotype }}</v-chip>
              </span>
            </div>
            <div class="gene-meta-item" style="align-items: flex-start;" v-if="locusData.apa_sites[0]?.species">
              <span class="gene-meta-label">Species</span>
              <span class="gene-meta-value">
                {{ formatSpeciesName(locusData.apa_sites[0].species) }}
                <span v-if="formatSpeciesSubtitle(locusData.apa_sites[0].species)" style="font-style: italic; opacity: 0.65; font-size: 13.5px;">{{ formatSpeciesSubtitle(locusData.apa_sites[0].species) }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- ── Genome Browser ───────────────────────────── -->
        <div class="section-card genome-browser-frame mb-6" v-if="transcriptStructure">
          <div class="section-title">
            <v-icon size="18" class="mr-2" style="color: #0D7377;">mdi-chart-gantt</v-icon>
            Genome Browser
            <v-chip size="small" variant="tonal" color="primary" class="ml-auto">
              Single Transcript View
            </v-chip>
          </div>
          <div class="panel-box">
            <div class="panel-body">
              <ApaGenomeBrowser
                :transcript-id="locusData.transcript.transcript_id"
                :gene-name="locusData.gene.gene_name"
                :chromosome="locusData.gene.chromosome"
                :strand="locusData.gene.strand"
                :exons="transcriptStructure.exons"
                :cds="transcriptStructure.cds"
                :apa-sites="locusData.apa_sites"
                :all-samples-info="locusData.samples"
              />
            </div>
          </div>
        </div>

        <!-- ── APA Sites Details ─────────────────────────────────────── -->
        <div class="section-card mb-6">
          <div class="section-title">
            <v-icon size="18" class="mr-2" style="color: #0D7377;">mdi-table</v-icon>
            PA Sites Details
            <div class="pas-legend ml-4">
              <span v-for="(meta, key) in pasLegendEntries" :key="key"
                class="pas-legend-item"
                :style="{ background: meta.bg, border: '1px solid ' + meta.border, color: meta.text }"
              >
                <span class="pas-chip-dot" :style="{ background: meta.border }"></span>
                {{ meta.label }}
              </span>
            </div>
          </div>
          <div class="panel-box">
            <div class="panel-body pa-0">
              <v-data-table
                :headers="tableHeaders"
                :items="flattenedTableData"
                :items-per-page="-1"
                hide-default-footer
                class="elegant-table"
                item-value="unified_id"
                v-model:expanded="seqOpen"
                :row-props="({ item }) => ({
                  class: seqOpen.includes(item.unified_id) ? 'row-seq-expanded ld-row-clickable' : 'ld-row-clickable',
                  onClick: () => toggleSeqPanel(item.unified_id)
                })"
              >
                <template v-slot:item.unified_id="{ item }">
                  <span class="ld-site-id-tag">{{ item.unified_id }}</span>
                </template>

                <template v-slot:item.cluster_range="{ item }">
                  <span class="ld-cluster-range">{{ item.cluster_range }}</span>
                </template>

                <template v-slot:item.mode_site_position="{ item }">
                  <code class="code-plain">{{ item.mode_site_position }}</code>
                </template>

                <template v-slot:item.pas_motif="{ item }">
                  <div v-if="item.pas_motif" class="d-flex align-center ga-1">
                    <span
                      class="pas-chip"
                      :style="{
                        background: pasTypeMeta(item.pas_type).bg,
                        border: '1px solid ' + pasTypeMeta(item.pas_type).border,
                        color: pasTypeMeta(item.pas_type).text,
                      }"
                    >
                      <span class="pas-chip-dot" :style="{ background: pasTypeMeta(item.pas_type).border }"></span>
                      {{ item.pas_motif }}
                    </span>
                    <span class="pas-type-label" :style="{ color: pasTypeMeta(item.pas_type).text }">
                      {{ pasTypeMeta(item.pas_type).label }}
                    </span>
                    <span
                      v-if="item.pas_position !== null && item.pas_position !== undefined"
                      class="text-caption text-grey"
                    >
                      {{ item.pas_position }}bp
                    </span>
                  </div>
                  <span
                    v-else
                    class="pas-chip pas-chip--none"
                    :style="{
                      background: pasTypeMeta(item.pas_type).bg,
                      border: '1px solid ' + pasTypeMeta(item.pas_type).border,
                      color: pasTypeMeta(item.pas_type).text,
                    }"
                  >
                    <span class="pas-chip-dot" :style="{ background: pasTypeMeta(item.pas_type).border }"></span>
                    {{ pasTypeMeta(item.pas_type).label }}
                  </span>
                </template>

                <template v-slot:item.pa_level="{ item }">
                  <span class="ld-pa-level">{{ item.pa_level || '—' }}</span>
                </template>

                <template v-slot:item.site_abundance="{ item }">
                  <div class="d-flex align-center ga-2">
                    <v-progress-linear
                      :model-value="item.site_abundance * 100"
                      color="primary"
                      height="6"
                      rounded
                      style="width: 80px;"
                    ></v-progress-linear>
                    <span class="ld-abundance-value">
                      {{ (item.site_abundance * 100).toFixed(1) }}%
                    </span>
                  </div>
                </template>

                <template v-slot:item.expand="{ item }">
                  <v-icon
                    size="18"
                    class="ld-chevron"
                    :class="{ 'ld-chevron-open': seqOpen.includes(item.unified_id) }"
                  >mdi-chevron-right</v-icon>
                </template>

                <template v-slot:header.site_abundance="{ column }">
                  <div class="ld-header-cell-row">
                    {{ column.title }}
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
                </template>

                <template v-slot:header.mode_site_position="{ column }">
                  <div class="ld-header-cell-row">
                    {{ column.title }}
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
                          The modal genomic coordinate of this PA site — the single nucleotide position most frequently observed as the cleavage-and-polyadenylation point across all supporting reads and samples.
                        </v-card-text>
                      </v-card>
                    </v-menu>
                  </div>
                </template>

                <template v-slot:header.cluster_range="{ column }">
                  <div class="ld-header-cell-row">
                    {{ column.title }}
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
                </template>

                <template v-slot:expanded-row="{ item }">
                  <tr class="seq-expanded-row">
                    <td :colspan="tableHeaders.length" class="pa-0">
                      <div class="detail-panel">

                        <div class="detail-panel-inner">

                          <!-- Sample Abundance -->
                          <div v-if="item.sample_details && item.sample_details.length > 0" class="detail-section">
                            <div class="detail-section-label">
                              <v-icon size="12" class="mr-1" style="color:#0D7377;">mdi-chart-bar</v-icon>
                              Sample Abundance
                              <span class="detail-section-sub">{{ item.sample_details.length }} sample{{ item.sample_details.length > 1 ? 's' : '' }}</span>
                            </div>
                            <div class="sample-abundance-list">
                              <div v-for="sd in item.sample_details" :key="sd.sample_name" class="sample-abundance-row">
                                <div class="sample-abundance-label">
                                  <v-chip size="x-small" variant="tonal" color="primary" class="sample-name-chip">{{ formatSampleName(sd.sample_name) }}</v-chip>
                                  <span class="sample-type-text">{{ formatSampleType(sd.sample_type) }}</span>
                                </div>
                                <div class="sample-abundance-bar">
                                   <v-progress-linear
                                    :model-value="(sd.site_abundance || 0) * 100"
                                    color="primary"
                                    height="6"
                                    rounded
                                    class="sample-bar-track"
                                  ></v-progress-linear>
                                  <span class="sample-pct-text">{{ ((sd.site_abundance || 0) * 100).toFixed(1) }}%</span>
                                </div>
                                <div class="sample-support-reads">
                                  <span>Supporting reads</span>
                                  <strong>{{ formatSupportingReads(sd.site_count) }}</strong>
                                </div>
                              </div>
                            </div>
                          </div>

                          <!-- Loading -->
                          <div v-if="seqData[item.unified_id]?.loading" class="detail-section d-flex align-center" style="min-height:60px">
                            <v-progress-circular indeterminate size="20" color="primary" />
                            <span class="ml-3 text-body-2 text-medium-emphasis">Fetching sequence…</span>
                          </div>

                          <!-- Error -->
                          <div v-else-if="seqData[item.unified_id]?.error" class="detail-section">
                            <v-alert type="error" variant="tonal" density="compact">{{ seqData[item.unified_id].error }}</v-alert>
                          </div>

                          <!-- Sequence viewer -->
                          <div v-else-if="seqData[item.unified_id]?.data" class="detail-section">
                            <div class="detail-section-label">
                              <v-icon size="12" class="mr-1" style="color:#0D7377;">mdi-map-marker-path</v-icon>
                              Genomic Sequence Context
                            </div>
                            <div class="seq-meta-row">
                              <span class="seq-meta-chip seq-meta-strand">
                                {{ seqData[item.unified_id].data.strand === '+' ? '(+) positive strand' : '(−) negative strand' }}
                              </span>
                              <span class="seq-meta-chip">
                                {{ seqData[item.unified_id].data.chromosome }}:{{
                                  (seqData[item.unified_id].data.mode_site_position - seqData[item.unified_id].data.flank).toLocaleString()
                                }}–{{
                                  (seqData[item.unified_id].data.mode_site_position + seqData[item.unified_id].data.flank).toLocaleString()
                                }}
                              </span>
                              <span class="seq-meta-chip seq-meta-window">±{{ seqData[item.unified_id].data.flank }} bp window</span>
                              <template v-if="seqData[item.unified_id].data.pas_motif">
                                <span
                                  class="seq-meta-chip seq-meta-pas"
                                  :style="{ background: pasTypeMeta(seqData[item.unified_id].data.pas_type).bg, border: '1px solid ' + pasTypeMeta(seqData[item.unified_id].data.pas_type).border, color: pasTypeMeta(seqData[item.unified_id].data.pas_type).text }"
                                >
                                  {{ seqData[item.unified_id].data.pas_motif }} · {{ pasTypeMeta(seqData[item.unified_id].data.pas_type).label }}
                                  <span
                                    v-if="seqData[item.unified_id].data.pas_position !== null && seqData[item.unified_id].data.pas_position !== undefined"
                                  > · {{ seqData[item.unified_id].data.pas_position }}bp</span>
                                </span>
                              </template>
                              <span class="seq-meta-chip seq-meta-pasite">
                                <v-icon size="11" style="color:#D45D79;">mdi-map-marker</v-icon>
                                Representative PA Site
                              </span>
                            </div>
                            <div class="seq-display">
                              <span
                                v-for="(nt, idx) in seqData[item.unified_id].data.sequence.split('')"
                                :key="idx"
                                :class="seqNtClass(nt, idx, seqData[item.unified_id].data)"
                                :style="seqNtStyle(nt, idx, seqData[item.unified_id].data)"
                                :title="idx === seqData[item.unified_id].data.cleavage_index ? 'Cleavage site' : ''"
                              >{{ nt }}</span>
                            </div>
                          </div>

                        </div>
                      </div>
                    </td>
                  </tr>
                </template>

              </v-data-table>
            </div>
          </div>
        </div>

        <!-- ── Abundance Heatmap ─────────────────────────────────────────── -->
        <div class="section-card mb-6" v-if="heatmapData.sites.length > 0">
          <div class="section-title">
            <v-icon size="18" class="mr-2" style="color: #0D7377;">mdi-view-grid-outline</v-icon>
            Per-site Abundance Heatmap
            <div class="heatmap-stats-chip ml-3">
              {{ heatmapData.sites.length }} site{{ heatmapData.sites.length !== 1 ? 's' : '' }}
              <span class="heatmap-stats-sep">×</span>
              {{ heatmapData.samples.length }} sample{{ heatmapData.samples.length !== 1 ? 's' : '' }}
            </div>
          </div>
          <div class="panel-box" style="overflow: visible;">
            <div class="panel-body pa-5">
              <div class="heatmap-wrap">
                <div class="heatmap-grid" :style="heatmapGridStyle">

                  <!-- ┌─ Corner ───────────────────────────────────────── -->
                  <div class="heatmap-corner">
                    <span class="heatmap-corner-text">PA&nbsp;Site</span>
                    <v-icon size="10" style="color:rgba(0,0,0,0.28);margin:0 2px;">mdi-arrow-right</v-icon>
                    <span class="heatmap-corner-text">Sample</span>
                  </div>

                  <!-- ┌─ Column headers (samples) ─────────────────────── -->
                  <div
                    v-for="(sample, si) in heatmapData.samples"
                    :key="sample"
                    class="heatmap-col-header"
                    :class="{ 'hm-col-active': hoverSampleName === sample }"
                    :title="formatSampleName(sample)"
                  >
                    <span
                      class="heatmap-sample-dot"
                      :style="{ background: heatmapSampleColor(si) }"
                    ></span>
                    <span class="heatmap-col-text">{{ formatSampleName(sample) }}</span>
                  </div>

                  <!-- ┌─ Data rows ────────────────────────────────────── -->
                  <template v-for="(site, si) in heatmapData.sites" :key="site.id">

                    <!-- Row label: numbered badge + full site ID, no position -->
                    <div class="heatmap-row-label" :class="{ 'hm-row-active': hoverSiteId === site.id }">
                      <span class="heatmap-site-badge" :style="heatmapBadgeStyle(si)">{{ si + 1 }}</span>
                      <span class="heatmap-site-id">{{ site.id }}</span>
                    </div>

                    <!-- Cells: plain divs; cross-hair highlight on hover -->
                    <div
                      v-for="sample in heatmapData.samples"
                      :key="sample"
                      class="heatmap-cell"
                      :class="heatmapCellClass(site.id, sample)"
                      :style="heatmapCellStyle(site.id, sample)"
                      @mouseenter="(e) => onCellEnter(e, site, sample)"
                      @mouseleave="onCellLeave"
                    >
                      <div class="heatmap-cell-inner">
                        <span
                          class="heatmap-cell-pct"
                          :style="{ color: heatmapTextColor(site.id, sample) }"
                        >{{ heatmapLabel(site.id, sample) }}</span>
                      </div>
                    </div>

                  </template>
                </div>

                <!-- ── Legend ──────────────────────────────────────────── -->
                <div class="heatmap-legend">
                  <div class="heatmap-legend-left">
                    <div class="heatmap-legend-scale">
                      <span class="heatmap-legend-tick">0%</span>
                      <div class="heatmap-legend-bar"></div>
                      <span class="heatmap-legend-tick">100%</span>
                    </div>
                    <span class="heatmap-legend-caption">Relative Abundance</span>
                  </div>
                  <div class="heatmap-legend-nd">
                    <span class="heatmap-legend-nd-swatch"></span>
                    <span class="heatmap-legend-nd-label">Not detected</span>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

      </div><!-- closes v-else-if="locusData" -->

    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiService } from '@/services/api'
import { formatSampleName, formatSampleType, formatSpeciesName, formatSpeciesSubtitle } from '@/utils/formatters'
import ApaGenomeBrowser from '@/components/ApaGenomeBrowser.vue'

const route = useRoute()

const loading = ref(true)
const error = ref(null)
const locusData = ref(null)
const transcriptStructure = ref(null)


// ── Sequence context panel ─────────────────────────────────────────────────
// seqOpen: array of site_ids whose sequence panel is expanded (v-model:expanded expects array)
// seqData: Map of unified_id → { loading, data, error }
const seqOpen = ref([])
const seqData = ref({})

const toggleSeqPanel = async (siteId) => {
  const idx = seqOpen.value.indexOf(siteId)
  if (idx !== -1) {
    seqOpen.value = seqOpen.value.filter(id => id !== siteId)
    return
  }
  seqOpen.value = [...seqOpen.value, siteId]

  // Fetch if not already loaded
  if (!seqData.value[siteId]) {
    seqData.value = { ...seqData.value, [siteId]: { loading: true, data: null, error: null } }
    try {
      const transcriptId = locusData.value.transcript.transcript_id
      const result = await apiService.getSiteSequence(
        transcriptId,
        siteId,
        50,
        locusData.value.apa_sites?.[0]?.species?.name
      )
      seqData.value = { ...seqData.value, [siteId]: { loading: false, data: result, error: null } }
    } catch (e) {
      seqData.value = { ...seqData.value, [siteId]: { loading: false, data: null, error: 'Failed to load sequence' } }
    }
  }
}

// Nucleotide colouring + cleavage/PAS highlighting
const seqNtClass = (nt, idx, data) => {
  if (idx === data.cleavage_index) return 'seq-nt seq-nt--cleavage'
  if (data.pas_motif && data.pas_position !== null && data.pas_position !== undefined) {
    const motifStart = data.cleavage_index + data.pas_position
    const motifEnd   = motifStart + data.pas_motif.length
    if (idx >= motifStart && idx < motifEnd) return 'seq-nt seq-nt--pas'
  }
  return 'seq-nt'
}

// Inline style for PAS motif — uses exact pasTypeMeta colours so it always matches the chip
const seqNtStyle = (nt, idx, data) => {
  if (idx === data.cleavage_index) return {}
  if (data.pas_motif && data.pas_position !== null && data.pas_position !== undefined) {
    const motifStart = data.cleavage_index + data.pas_position
    const motifEnd   = motifStart + data.pas_motif.length
    if (idx >= motifStart && idx < motifEnd) {
      const meta = pasTypeMeta(data.pas_type)
      return { background: meta.bg, color: meta.text }
    }
  }
  return {}
}

const tableHeaders = [
  { title: '', key: 'expand', sortable: false, width: 48 },
  { title: 'Site ID', key: 'unified_id', sortable: true },
  { title: 'Cluster Range', key: 'cluster_range', sortable: true },
  { title: 'Rep. Position', key: 'mode_site_position', sortable: true },
  { title: 'PAS Motif', key: 'pas_motif', sortable: true },
  { title: 'PAS Level', key: 'pa_level', sortable: true, width: 96, align: 'center' },
  { title: 'Mean Abundance', key: 'site_abundance', sortable: true, width: 150 },
]

const displayBiotype = computed(() => {
  const raw = locusData.value?.apa_sites?.[0]?.transcript_biotype
  if (!raw) return null
  if (raw === 'protein_coding') return 'mRNA'
  if (raw.toLowerCase().includes('lnc')) return 'lncRNA'
  return raw
})

const representativePriority = {
  MANE_Select: 1,
  RefSeq_Select: 2,
  Ensembl_Canonical: 3,
  APPRIS_Principal: 4
}

const transcriptRepresentativeStatus = computed(() => {
  const statuses = (locusData.value?.apa_sites || [])
    .map(site => site.representative_status)
    .filter(status => status && status !== 'not_representative')
  if (!statuses.length) return null
  return statuses.sort((a, b) =>
    (representativePriority[a] || 99) - (representativePriority[b] || 99)
  )[0]
})

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
    MANE_Select: 'transcript-representative-badge--mane',
    RefSeq_Select: 'transcript-representative-badge--refseq',
    Ensembl_Canonical: 'transcript-representative-badge--ensembl',
    APPRIS_Principal: 'transcript-representative-badge--appris'
  }[status] || 'transcript-representative-badge--default'
}

const formatClusterRange = (site) => {
  if (site.cluster_start == null || site.cluster_end == null) return '—'
  return `${site.cluster_start}:${site.cluster_end}`
}

const formatSupportingReads = count =>
  Number.isSafeInteger(count) && count >= 0 ? count.toLocaleString() : 'N/A'

const dedupeSampleDetails = (details) => {
  const seen = new Set()
  return (details || []).filter(detail => {
    const key = formatSampleName(detail.sample_name).toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const flattenedTableData = computed(() => {
  if (!locusData.value) return []
  return locusData.value.apa_sites.map(site => {
    const samples = dedupeSampleDetails(site.sample_details)
    const avgAbundance = samples.length > 0
      ? samples.reduce((sum, sd) => sum + (sd.site_abundance || 0), 0) / samples.length
      : site.site_abundance || 0
    return {
      unified_id: site.unified_id,
      cluster_range: formatClusterRange(site),
      mode_site_position: site.mode_site_position,
      pas_motif: site.pas_motif,
      pas_position: site.pas_position,
      pas_type: site.pas_type,
      pa_level: site.pa_level,
      sample_count: samples.length,
      site_abundance: avgAbundance,
      site_count: site.site_count,
      sample_details: samples,
    }
  })
})

// ── Heatmap ────────────────────────────────────────────────────────────────

// Build the flat lookup: { [siteId]: { [sampleName]: { abundance, count } } }
const heatmapLookup = computed(() => {
  if (!locusData.value) return {}
  const lookup = {}
  for (const site of locusData.value.apa_sites) {
    lookup[site.unified_id] = {}
    for (const sd of dedupeSampleDetails(site.sample_details)) {
      lookup[site.unified_id][formatSampleName(sd.sample_name).toLowerCase()] = {
        abundance: sd.site_abundance,
        count: sd.site_count
      }
    }
  }
  return lookup
})

const heatmapData = computed(() => {
  if (!locusData.value) return { sites: [], samples: [] }
  // samples may be [{name, sample_type}] objects or plain strings — normalise to strings
  const seenSamples = new Set()
  const allSamples = (locusData.value.samples || [])
    .map(s => s?.name ?? s)
    .filter(sample => {
      const key = formatSampleName(sample).toLowerCase()
      if (!key || seenSamples.has(key)) return false
      seenSamples.add(key)
      return true
    })
  const sites = locusData.value.apa_sites.map(s => ({
    id: s.unified_id,
    position: s.mode_site_position
  }))
  // Sort sites by position (proximal → distal)
  const strand = locusData.value.gene.strand
  sites.sort((a, b) => strand === '-' ? b.position - a.position : a.position - b.position)
  return { sites, samples: allSamples }
})

const heatmapGridStyle = computed(() => {
  const n = heatmapData.value.samples.length
  // Fixed sample columns keep cell geometry stable while labels wrap in the header.
  return {
    display: 'grid',
    gridTemplateColumns: `max-content repeat(${n}, 92px)`,
    gap: '3px'
  }
})

const HEATMAP_COLOR = [13, 115, 119]   // RGB of primary teal #0D7377

const heatmapCellStyle = (siteId, sample) => {
  const entry = heatmapLookup.value[siteId]?.[formatSampleName(sample).toLowerCase()]
  if (!entry) {
    return {
      background: 'repeating-linear-gradient(45deg, rgba(0,0,0,0.03) 0px, rgba(0,0,0,0.03) 4px, rgba(0,0,0,0.06) 4px, rgba(0,0,0,0.06) 8px)',
      border: '1px solid rgba(0,0,0,0.08)'
    }
  }
  const alpha = Math.max(0.08, entry.abundance)
  const [r, g, b] = HEATMAP_COLOR
  return {
    background: `rgba(${r},${g},${b},${alpha})`,
    border: '1px solid rgba(0,0,0,0.06)'
  }
}

const heatmapTextColor = (siteId, sample) => {
  const entry = heatmapLookup.value[siteId]?.[formatSampleName(sample).toLowerCase()]
  if (!entry) return 'rgba(0,0,0,0.3)'
  return entry.abundance > 0.5 ? '#ffffff' : '#1a1a1a'
}

const heatmapLabel = (siteId, sample) => {
  const entry = heatmapLookup.value[siteId]?.[formatSampleName(sample).toLowerCase()]
  if (!entry) return '—'
  return (entry.abundance * 100).toFixed(0) + '%'
}

// ── Heatmap visual helpers ──────────────────────────────────────────────────

const HEATMAP_SAMPLE_COLORS = [
  '#0D7377', '#355C7D', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#EF4444', '#8B5CF6'
]
const heatmapSampleColor = (idx) => HEATMAP_SAMPLE_COLORS[idx % HEATMAP_SAMPLE_COLORS.length]

const BADGE_GRADIENTS = [
  ['#0D7377', '#14919B'],
  ['#355C7D', '#4A7898'],
  ['#EC4899', '#F472B6'],
  ['#F59E0B', '#FCD34D'],
  ['#10B981', '#34D399'],
  ['#3B82F6', '#60A5FA'],
  ['#EF4444', '#F87171'],
  ['#8B5CF6', '#A78BFA'],
]
const heatmapBadgeStyle = (idx) => {
  const [c1, c2] = BADGE_GRADIENTS[idx % BADGE_GRADIENTS.length]
  return { background: `linear-gradient(135deg, ${c1}, ${c2})` }
}

// ── Heatmap cross-hair hover state ─────────────────────────────────────────
const hoverSiteId = ref(null)
const hoverSampleName = ref(null)

function onCellEnter(_event, site, sample) {
  hoverSiteId.value = site.id
  hoverSampleName.value = sample
}

function onCellLeave() {
  hoverSiteId.value = null
  hoverSampleName.value = null
}

const heatmapCellClass = (siteId, sample) => {
  if (hoverSiteId.value === null) return ''
  const inRow = hoverSiteId.value === siteId
  const inCol = hoverSampleName.value === sample
  if (inRow && inCol) return 'hm-cross-intersection'
  if (inRow || inCol) return 'hm-cross-arm'
  return 'hm-dimmed'
}

const PAS_TYPE_META = {
  canonical  : { label: 'Canonical',   bg: 'rgba(13,115,119,0.18)',  border: '#269095', text: '#055B60' },
  variant    : { label: 'Variant',     bg: 'rgba(53,92,125,0.18)',   border: '#4F7FA4', text: '#275A7B' },
  upstream   : { label: 'Upstream',    bg: 'rgba(169,111,76,0.19)',  border: '#A96F4C', text: '#7A472B' },
  downstream : { label: 'Downstream',  bg: 'rgba(116,106,158,0.18)', border: '#7F73B3', text: '#574C88' },
  plant_nue  : { label: 'Plant NUE',   bg: 'rgba(32,130,111,0.17)',  border: '#3A927F', text: '#176353' },
  plant_fue  : { label: 'Plant FUE',   bg: 'rgba(125,142,76,0.18)',  border: '#84934F', text: '#59652E' },
  yeast_ee_pe: { label: 'Yeast EE + PE', bg: 'rgba(45,118,140,0.17)', border: '#4A8297', text: '#285C70' },
  yeast_positioning: { label: 'Yeast PE', bg: 'rgba(185,139,57,0.17)', border: '#B58A3F', text: '#75591F' },
  yeast_efficiency: { label: 'Yeast EE', bg: 'rgba(169,111,76,0.17)', border: '#A96F4C', text: '#75492F' },
  yeast_u_rich: { label: 'Yeast U-rich', bg: 'rgba(91,126,108,0.16)', border: '#668574', text: '#3F5F4E' },
  pombe_a_rich: { label: 'S. pombe A-rich', bg: 'rgba(35,125,121,0.17)', border: '#3D8B87', text: '#1B615E' },
  pombe_gua_uag: { label: 'S. pombe GUA/UAG', bg: 'rgba(104,103,151,0.17)', border: '#7775A5', text: '#52517C' },
  pombe_uag: { label: 'S. pombe UAG', bg: 'rgba(122,105,153,0.17)', border: '#8674A5', text: '#5B4D77' },
  pombe_gua: { label: 'S. pombe GUA', bg: 'rgba(80,117,151,0.17)', border: '#6483A0', text: '#405F79' },
  pombe_u_rich: { label: 'S. pombe U-rich', bg: 'rgba(105,128,106,0.16)', border: '#758C76', text: '#4C654D' },
  not_assessed: { label: 'Not assessed', bg: 'rgba(100,116,139,0.08)', border: '#CBD5E1', text: '#64748B' },
  none       : { label: 'None',        bg: 'rgba(100,116,139,0.08)', border: '#CBD5E1', text: '#64748B' },
}
const pasTypeMeta = (type) => PAS_TYPE_META[type] ?? PAS_TYPE_META.none
const pasLegendEntries = computed(() => {
  const types = new Set(flattenedTableData.value.map(item => item.pas_type || 'none'))
  return Object.fromEntries(
    [...types].map(type => [type, pasTypeMeta(type)])
  )
})

onMounted(async () => {
  const transcriptId = route.params.transcriptId
  const species = route.query.species
  
  loading.value = true
  error.value = null
  
  try {
    // Fetch locus data first — this is required for the page
    const locusResponse = await apiService.getLocusDetail(transcriptId, species)
    locusData.value = locusResponse

    // Fetch transcript structure separately — failure is non-fatal
    apiService.getTranscriptStructure(transcriptId, species)
      .then(structureResponse => {
        transcriptStructure.value = structureResponse
      })
      .catch(structureErr => {
        console.warn('Transcript structure not available:', structureErr)
        // Page still works without structure (genome browser will be hidden)
      })

  } catch (err) {
    console.error('Failed to load locus detail:', err)
    error.value = 'Failed to load locus details. Please try again.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.locus-detail-page {
  min-height: 100vh;
  background: #f8fafc;
}

a {
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* ── Gene/Transcript header card ─────────────────────────────────── */
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
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.gene-name-text {
  font-size: 1.6rem;
  font-weight: 700;
  color: rgba(0,0,0,0.87);
  letter-spacing: -0.01em;
}

.transcript-representative-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 1px 7px;
  border-radius: 999px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: 0.02em;
  white-space: nowrap;
  border: 1px solid rgba(100, 116, 139, 0.22);
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
  transform: translateY(1px);
}

.transcript-representative-badge--mane {
  color: #0f766e;
  background: rgba(240, 253, 250, 0.88);
  border-color: rgba(13, 148, 136, 0.22);
}

.transcript-representative-badge--refseq {
  color: #355c7d;
  background: rgba(241, 245, 249, 0.95);
  border-color: rgba(53, 92, 125, 0.22);
}

.transcript-representative-badge--ensembl {
  color: #3f6f56;
  background: rgba(242, 248, 244, 0.92);
  border-color: rgba(63, 111, 86, 0.22);
}

.transcript-representative-badge--appris {
  color: #9a5b13;
  background: rgba(255, 251, 235, 0.9);
  border-color: rgba(194, 120, 25, 0.24);
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

.gene-id-link {
  font-weight: 600;
  color: #0D7377;
  text-decoration: none;
}

.gene-id-link:hover {
  color: #14919B;
  text-decoration: underline;
}

/* ── Section card ─────────────────────────────────────────────────── */
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

/* ── Panel box ────────────────────────────────────────────────────── */
.panel-box {
  border: 1px solid rgba(13, 115, 119, 0.14);
  border-radius: 12px;
  overflow: hidden;
  background: #f8fbfb !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  box-shadow: none !important;
}

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

.panel-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
}

.panel-icon-teal {
  background: #0D7377;
}

.panel-title-text {
  font-size: 1.02rem;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.82);
  line-height: 1.3;
}

.panel-subtitle-text {
  font-size: 0.86rem;
  color: rgba(0, 0, 0, 0.46);
  margin-top: 2px;
  max-width: 480px;
}

.panel-body {
  padding: 16px;
}

.pas-motif {
  font-weight: 600;
  color: #0D7377;
  letter-spacing: 0.5px;
}

/* ── PAS motif type chips ─────────────────────────────────────────── */
.pas-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: 'IBM Plex Mono', 'Courier New', monospace;
  letter-spacing: 0.3px;
  white-space: nowrap;
  line-height: 1.6;
}

.pas-chip--none {
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid #BDBDBD;
  color: #757575;
  font-family: 'IBM Plex Sans', sans-serif;
  font-style: italic;
}

.pas-chip-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pas-type-label {
  font-size: 12.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-weight: 500;
  opacity: 0.85;
}

/* ── PAS legend strip ─────────────────────────────────────────────── */
.pas-legend {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
  font-weight: 400;
}

.pas-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px 2px 6px;
  border-radius: 20px;
  font-size: 12.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-weight: 500;
  white-space: nowrap;
}

.elegant-table :deep(code) {
  background: rgba(13, 115, 119, 0.08);
  color: #0D7377;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'IBM Plex Sans', sans-serif;
}

.elegant-table :deep(code.code-plain) {
  background: none;
  border-radius: 10px;
  padding: 2px 9px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
}

.light-card-bg {
  background: rgba(var(--v-theme-surface), 0.5) !important;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.elegant-table {
  background: transparent !important;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 14.5px;
}

.elegant-table :deep(.v-data-table__th) {
  background: rgba(13, 115, 119, 0.04) !important;
  font-size: 12.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: #475569 !important;
  border-bottom: 1px solid rgba(13, 115, 119, 0.10) !important;
  white-space: nowrap;
  font-family: 'IBM Plex Sans', sans-serif;
}

.elegant-table :deep(.v-data-table__td) {
  padding: 11px 16px;
  background: transparent !important;
  color: rgba(0, 0, 0, 0.82);
  border-bottom: 1px solid rgba(0, 0, 0, 0.055) !important;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
}

/* When row is expanded: suppress the full-width td borders */
.elegant-table :deep(.row-seq-expanded .v-data-table__td) {
  border-bottom: none !important;
}

.elegant-table :deep(.v-data-table__tr:hover .v-data-table__td) {
  background: rgba(13, 115, 119, 0.04) !important;
}

.elegant-table :deep(.v-data-table-footer) {
  background: transparent !important;
  border-top: 1px solid rgba(13, 115, 119, 0.10) !important;
  font-size: 13.5px;
  color: rgba(0, 0, 0, 0.60);
}

.elegant-table :deep(.v-data-table) {
  background: transparent !important;
}

.elegant-table :deep(table) {
  background: transparent !important;
}

.elegant-table :deep(tbody) {
  background: transparent !important;
}

.elegant-table :deep(thead) {
  background: rgba(13, 115, 119, 0.04) !important;
}

/* ── Heatmap ──────────────────────────────────────────────────────── */
.heatmap-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.heatmap-grid {
  min-width: 300px;
  max-width: max-content;
  border: 1px solid rgba(13, 115, 119, 0.14);
  box-shadow: 0 2px 14px rgba(13, 115, 119, 0.07);
  border-radius: 8px;
}

/* ── Corner cell ── */
.heatmap-corner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 10px 12px;
  background: rgba(13, 115, 119, 0.07);
  border-right: 1px solid rgba(13, 115, 119, 0.12);
  border-bottom: 2px solid rgba(13, 115, 119, 0.12);
  min-height: 46px;
}

.heatmap-corner-text {
  font-size: 10.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.38);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

/* ── Column headers ── */
.heatmap-col-header {
  display: grid;
  grid-template-rows: 12px minmax(0, auto);
  justify-items: center;
  align-items: start;
  padding: 8px 7px 9px;
  gap: 5px;
  background: rgba(13, 115, 119, 0.04);
  border-bottom: 2px solid rgba(13, 115, 119, 0.12);
  border-right: 1px solid rgba(13, 115, 119, 0.07);
  min-height: 72px;
  min-width: 0;
}

.heatmap-sample-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  align-self: center;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.85), 0 1px 4px rgba(0, 0, 0, 0.15);
}

.heatmap-col-text {
  display: block;
  width: 100%;
  font-size: 11.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.62);
  letter-spacing: 0.2px;
  line-height: 1.25;
  text-align: center;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: normal;
}

/* ── Row labels ── */
.heatmap-row-label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px 0 10px;
  background: rgba(13, 115, 119, 0.03);
  border-right: 2px solid rgba(13, 115, 119, 0.12);
  border-bottom: 1px solid rgba(13, 115, 119, 0.07);
  min-height: 44px;
}

.heatmap-site-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  border-radius: 50%;
  color: white;
  font-size: 11px;
  font-weight: 700;
  font-family: 'IBM Plex Sans', sans-serif;
  flex-shrink: 0;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.22);
  letter-spacing: -0.2px;
}

.heatmap-site-id {
  font-size: 12px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.80);
  white-space: nowrap;
  cursor: default;
  letter-spacing: -0.2px;
}

/* ── Cells ── */
.heatmap-cell {
  min-height: 44px;
  cursor: default;
  transition: opacity 0.12s ease, box-shadow 0.12s ease;
  position: relative;
  border-right: 1px solid rgba(255, 255, 255, 0.18);
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}

/* ── Cross-hair highlight ── */
.heatmap-cell.hm-dimmed {
  opacity: 0.30;
}

.heatmap-cell.hm-cross-arm {
  box-shadow: inset 0 0 0 1.5px rgba(13, 115, 119, 0.45);
  filter: brightness(1.12);
}

.heatmap-cell.hm-cross-intersection {
  box-shadow: inset 0 0 0 2px rgba(13, 115, 119, 0.90);
  filter: brightness(1.22);
  z-index: 1;
}

.hm-row-active {
  background: rgba(13, 115, 119, 0.10) !important;
}

.hm-col-active {
  background: rgba(13, 115, 119, 0.08) !important;
}

.heatmap-cell-inner {
  width: 100%;
  height: 100%;
  min-height: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px 4px;
}

.heatmap-cell-pct {
  font-size: 11.5px;
  font-weight: 700;
  font-family: 'IBM Plex Sans', sans-serif;
  line-height: 1;
  letter-spacing: -0.3px;
}

/* ── Stats chip in section title ── */
.heatmap-stats-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 20px;
  background: rgba(13, 115, 119, 0.08);
  border: 1px solid rgba(13, 115, 119, 0.16);
  font-size: 12px;
  font-weight: 500;
  color: #0D7377;
  font-family: 'IBM Plex Sans', sans-serif;
}

.heatmap-stats-sep {
  opacity: 0.48;
  font-size: 11px;
}

/* ── Legend ── */
.heatmap-legend {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.heatmap-legend-left {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.heatmap-legend-scale {
  display: flex;
  align-items: center;
  gap: 8px;
}

.heatmap-legend-tick {
  font-size: 11.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  color: rgba(0, 0, 0, 0.48);
  min-width: 26px;
}

.heatmap-legend-tick:last-child {
  text-align: right;
}

.heatmap-legend-bar {
  width: 180px;
  height: 11px;
  border-radius: 6px;
  background: linear-gradient(
    to right,
    rgba(13, 115, 119, 0.06),
    rgba(13, 115, 119, 0.28),
    rgba(13, 115, 119, 0.62),
    rgba(13, 115, 119, 1.0)
  );
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.heatmap-legend-caption {
  font-size: 10.5px;
  font-family: 'IBM Plex Sans', sans-serif;
  color: rgba(0, 0, 0, 0.38);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  padding-left: 2px;
}

.heatmap-legend-nd {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.09);
  background: rgba(0, 0, 0, 0.015);
}

.heatmap-legend-nd-swatch {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: repeating-linear-gradient(
    45deg,
    rgba(0, 0, 0, 0.04) 0px,
    rgba(0, 0, 0, 0.04) 3px,
    rgba(0, 0, 0, 0.10) 3px,
    rgba(0, 0, 0, 0.10) 6px
  );
  border: 1px solid rgba(0, 0, 0, 0.12);
}

.heatmap-legend-nd-label {
  font-size: 12px;
  font-family: 'IBM Plex Sans', sans-serif;
  color: rgba(0, 0, 0, 0.48);
}

/* ── Site ID tag (outer table) ───────────────────────────────────── */
.ld-site-id-tag {
  display: inline-block;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.10);
  border: 1px solid rgba(13, 115, 119, 0.22);
  border-radius: 10px;
  padding: 2px 9px;
  white-space: nowrap;
  cursor: default;
}

.ld-cluster-range {
  display: inline-block;
  color: rgba(15, 23, 42, 0.78);
  background: rgba(53, 92, 125, 0.08);
  border: 1px solid rgba(53, 92, 125, 0.16);
  border-radius: 10px !important;
  padding: 2px 9px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  white-space: nowrap;
}

.ld-pa-level {
  display: inline-block;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.10);
  border: 1px solid rgba(13, 115, 119, 0.22);
  border-radius: 10px !important;
  padding: 2px 9px;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  white-space: nowrap;
}

.ld-abundance-value {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
}

/* ── Row expand chevron ──────────────────────────────────────────── */
.ld-row-clickable {
  cursor: pointer;
}

.ld-chevron {
  color: rgba(13, 115, 119, 0.45);
  transition: color 0.15s ease, transform 0.2s ease;
  display: block;
}

.ld-row-clickable:hover .ld-chevron {
  color: #0D7377;
}

.ld-chevron-open {
  transform: rotate(90deg);
  color: #0D7377;
}

/* ── Expanded row container ──────────────────────────────────────── */
.seq-expanded-row td {
  background: transparent !important;
  padding: 0 !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.055) !important;
  vertical-align: top;
}

.detail-panel {
  width: 100%;
  box-sizing: border-box;
  background: #f6faf9;
  border-top: 1px solid rgba(13, 115, 119, 0.12);
  padding: 14px 18px 18px 5%;
}

.detail-panel-inner {
  box-sizing: border-box;
  width: 100%;
  padding: 14px 18px 16px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid rgba(13, 115, 119, 0.12);
  border-radius: 10px;
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03);
}

.detail-section {
  box-sizing: border-box;
  width: 100%;
  padding: 14px 0 14px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.055);
}

.detail-section:last-child {
  border-bottom: none;
}

.detail-section-label {
  display: flex;
  align-items: center;
  font-size: 12.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: #0D7377;
  margin-bottom: 8px;
  gap: 2px;
}

.detail-section-sub {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: rgba(0, 0, 0, 0.35);
  font-style: italic;
  margin-left: 4px;
}

/* ── Sample abundance ────────────────────────────────────────────── */
.sample-abundance-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 6px;
}

.sample-abundance-row {
  display: grid;
  grid-template-columns: minmax(120px, 220px) minmax(0, 1fr) 176px;
  align-items: center;
  gap: 12px;
  min-height: 24px;
}

.sample-abundance-label {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.sample-name-chip {
  flex-shrink: 0;
  font-size: 12px !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
}

.sample-type-text {
  font-size: 11px;
  font-family: 'IBM Plex Sans', sans-serif;
  color: rgba(0, 0, 0, 0.38);
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sample-abundance-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.sample-bar-track { flex: 1; min-width: 0; }

.sample-pct-text {
  font-size: 12px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.55);
  width: 44px;
  flex-shrink: 0;
  font-family: 'IBM Plex Sans', sans-serif;
}

.sample-support-reads {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding-left: 12px;
  border-left: 1px solid #e2e8f0;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.sample-support-reads strong {
  color: #0f172a;
  font-weight: 600;
}

/* ── Sequence viewer ─────────────────────────────────────────────── */
.seq-meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding-bottom: 8px;
}

.seq-meta-chip {
  display: inline-flex;
  align-items: center;
  line-height: 1;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.06);
  color: rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(0, 0, 0, 0.10);
}

.seq-meta-strand {
  background: rgba(13, 115, 119, 0.10);
  color: #0D7377;
  border-color: rgba(13, 115, 119, 0.25);
}

.seq-meta-window {
  background: rgba(0, 0, 0, 0.04);
}

.seq-meta-pasite {
  background: rgba(212, 93, 121, 0.08);
  border-color: rgba(212, 93, 121, 0.25);
  color: rgba(0, 0, 0, 0.55);
  gap: 4px;
}

.seq-display {
  box-sizing: border-box;
  width: 100%;
  font-family: 'IBM Plex Mono', 'Courier New', monospace;
  font-size: 14.5px;
  line-height: 1.6;
  letter-spacing: 0.05em;
  white-space: nowrap;
  overflow-x: auto;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  padding: 8px 0 2px;
}

.seq-nt {
  display: inline;
  color: rgba(0, 0, 0, 0.82);
}

.seq-nt--pas {
  border-radius: 2px;
  font-weight: 700;
}

.seq-nt--cleavage {
  background: #D45D79;
  color: #fff;
  border-radius: 3px;
  padding: 0 1px;
  font-weight: 700;
}

/* ── Mean Abundance header with popover ─────────────────────────── */
.ld-header-cell-row {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
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
  width: 100%;
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

@media (max-width: 900px) {
  .gene-meta-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .gene-meta-item {
    align-items: flex-start;
    min-width: 0;
  }

  .section-title {
    align-items: flex-start;
    gap: 8px;
  }

  .pas-legend {
    width: 100%;
    margin-left: 0 !important;
    margin-top: 8px;
  }

  .elegant-table :deep(.v-table__wrapper) {
    overflow-x: auto;
  }

  .elegant-table :deep(table) {
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
  .locus-detail-page :deep(.v-container) {
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
    font-size: 1.2rem;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }

  .gene-meta-row {
    grid-template-columns: 1fr;
  }

  .section-title {
    font-size: 1.04rem;
    line-height: 1.3;
  }

  .panel-body {
    padding: 12px;
  }

  .panel-body.pa-0 {
    padding: 0 !important;
  }

  .pas-legend {
    gap: 6px;
  }

  .pas-legend-item {
    font-size: 10.5px;
    padding: 3px 7px;
  }

  .seq-context-card {
    padding: 12px;
  }

  .seq-display {
    font-size: 13px;
  }
}
</style>
