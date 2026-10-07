<template>
  <div>
    <section class="hero-section">
      <div class="hero-bg"></div>
      <v-container class="hero-content">
        <v-row justify="center">
          <v-col cols="12" md="10" lg="8">
            <div class="text-center mb-8">
              <h1 class="text-h2 text-white font-weight-bold mb-4">
                <IsoAPAIcon :size="48" class="mr-3" style="color:white;" />
                IsoAPA
              </h1>
              <p class="hero-subtitle mb-8">
                Isoform-Level Alternative Polyadenylation Database
              </p>
            </div>
            
            <v-card class="search-card pa-2" elevation="8">
              <v-text-field
                v-model="searchQuery"
                placeholder="Search by gene name, transcript ID, sample..."
                prepend-inner-icon="mdi-magnify"
                variant="solo"
                flat
                hide-details
                @keyup.enter="performSearch"
              ></v-text-field>
              <v-card-actions class="px-4 pb-4">
                <div class="home-field-selector" role="group" aria-label="Search field">
                  <button
                    v-for="field in searchFields"
                    :key="field.value"
                    class="home-field-chip"
                    :class="{ 'home-field-chip--active': selectedField === field.value }"
                    type="button"
                    @click="selectedField = field.value"
                  >
                    {{ field.label }}
                  </button>
                </div>
                <v-spacer></v-spacer>
                <v-btn color="primary" size="large" @click="performSearch">
                  Search
                </v-btn>
              </v-card-actions>
            </v-card>
            
            <div class="text-center mt-6">
              <v-btn variant="text" color="white" to="/search" class="mr-4">
                <v-icon start>mdi-view-list</v-icon>
                Browse All Data
              </v-btn>
              <v-btn variant="text" color="white" to="/compare">
                <v-icon start>mdi-vector-link</v-icon>
                Compare Orthologs
              </v-btn>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </section>
    
    <section class="info-section py-16">
      <v-container>
        <div class="text-center mb-12">
          <div class="section-eyebrow mb-2">What is Isoform-Level APA?</div>
          <h2 class="text-h4 font-weight-bold mb-3">Isoform-Resolved 3′ End Variation</h2>
          <p class="text-body-1 text-grey-darken-1" style="max-width: 720px; margin: 0 auto;">
            IsoAPA maps polyadenylation sites to individual transcript isoforms, revealing alternative
            3′ end usage that is hidden by gene-level summaries.
          </p>
        </div>
        
        <v-row justify="center" align="stretch" class="mb-6">
          <!-- Left Panel: Transcript Structure -->
          <v-col cols="12" lg="6" class="d-flex flex-column col-diagram">
            <div class="apa-diagram-card flex-grow-1 pa-6">
              <div class="d-flex justify-space-between align-center mb-6">
                <h3 class="text-h6 font-weight-bold">Same Isoform Structure · Alternative 3′ Ends</h3>
                <div class="diagram-legend">
                  <div class="legend-item">
                    <div class="legend-color-box bg-teal-gradient"></div>
                    <span>CDS Exon</span>
                  </div>
                  <div class="legend-item">
                    <div class="legend-color-box bg-utr-gradient"></div>
                    <span>3' UTR</span>
                  </div>
                </div>
              </div>

              <div class="diagram-track-container">
                <!-- Short Isoform -->
                <div class="diagram-track mb-8">
                  <div class="mb-3">
                    <span class="text-subtitle-2 font-weight-bold">Proximal PAS</span>
                  </div>
                  <div class="d-flex align-center gap-3">
                    <div class="diagram-visual flex-grow-1">
                      <div class="diagram-spine"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-intron"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-intron"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-utr short"></div>
                      <div class="diagram-pas-marker">▼</div>
                    </div>
                    <v-chip size="x-small" color="primary" variant="tonal" class="flex-shrink-0">Short Isoform</v-chip>
                  </div>
                </div>

                <!-- Long Isoform -->
                <div class="diagram-track">
                  <div class="mb-3">
                    <span class="text-subtitle-2 font-weight-bold">Distal PAS</span>
                  </div>
                  <div class="d-flex align-center gap-3">
                    <div class="diagram-visual flex-grow-1">
                      <div class="diagram-spine"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-intron"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-intron"></div>
                      <div class="diagram-exon"></div>
                      <div class="diagram-utr long"></div>
                      <div class="diagram-pas-marker">▼</div>
                    </div>
                    <v-chip size="x-small" color="error" variant="tonal" class="flex-shrink-0">Long Isoform</v-chip>
                  </div>
                </div>
              </div>

              <div class="diagram-note mt-6 pt-5">
                <p class="text-caption text-grey-darken-1 mb-0">
                  Both isoforms encode the same protein. The longer 3′ UTR of the distal isoform,
                  however, harbors additional miRNA target sites and RNA-binding protein (RBP) motifs
                  that govern mRNA stability, localization, and translational output — regulatory
                  information invisible to gene-level expression analysis.
                </p>
              </div>
            </div>
          </v-col>
          
          <!-- Right Panel: Why APA Matters (2x2 Grid) -->
          <v-col cols="12" lg="6" class="d-flex flex-column col-why">
            <h3 class="text-h6 font-weight-bold mb-4 px-2">Why Isoform-Level APA Matters</h3>
            <v-row dense class="flex-grow-1">
              <v-col cols="12" sm="6" lg="6">
                <div class="why-mini-card h-100 pa-4">
                  <v-icon icon="mdi-chart-line" color="primary" size="28" class="mb-3"></v-icon>
                  <div class="text-subtitle-2 font-weight-bold mb-1">mRNA Stability</div>
                  <div class="text-caption text-grey-darken-1">Longer 3′ UTRs expose AU-rich elements that tune mRNA half-life and translation rate</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" lg="6">
                <div class="why-mini-card h-100 pa-4">
                  <v-icon icon="mdi-magnet" color="primary" size="28" class="mb-3"></v-icon>
                  <div class="text-subtitle-2 font-weight-bold mb-1">miRNA Escape</div>
                  <div class="text-caption text-grey-darken-1">Short isoforms lose miRNA binding sites, shielding oncogenes from repression in cancer</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" lg="6">
                <div class="why-mini-card h-100 pa-4">
                  <v-icon icon="mdi-map-marker-radius" color="primary" size="28" class="mb-3"></v-icon>
                  <div class="text-subtitle-2 font-weight-bold mb-1">Subcellular Targeting</div>
                  <div class="text-caption text-grey-darken-1">3′ UTR sequences direct mRNAs to specific compartments — dendrites, stress granules, and beyond</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" lg="6">
                <div class="why-mini-card h-100 pa-4">
                  <v-icon icon="mdi-hospital-building" color="error" size="28" class="mb-3"></v-icon>
                  <div class="text-subtitle-2 font-weight-bold mb-1">Disease Relevance</div>
                  <div class="text-caption text-grey-darken-1">APA dysregulation is a hallmark of cancer, neurodegeneration, and immune disorders</div>
                </div>
              </v-col>
            </v-row>
          </v-col>
        </v-row>

      </v-container>
    </section>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import IsoAPAIcon from '@/components/IsoAPAIcon.vue'

const router = useRouter()

const searchQuery = ref('')
const selectedField = ref('gene_name')
const searchFields = [
  { value: 'gene_name', label: 'Gene Name' },
  { value: 'transcript_id', label: 'Transcript ID' },
  { value: 'sample', label: 'Sample' },
  { value: 'species', label: 'Species' }
]

const performSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({
      path: '/search',
      query: { 
        [selectedField.value]: searchQuery.value 
      }
    })
  } else {
    router.push('/search')
  }
}

</script>

<style scoped>
/* ── Hero ─────────────────────────────────────────────────── */
.hero-section {
  position: relative;
  min-height: 520px;
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

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.hero-content {
  position: relative;
  z-index: 1;
  padding: 56px 0 64px;
}

.hero-subtitle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 780px;
  color: rgba(255, 255, 255, 0.96);
  font-size: clamp(1.22rem, 2.3vw, 1.65rem);
  font-weight: 600;
  line-height: 1.45;
  letter-spacing: 0.01em;
  text-shadow: 0 2px 12px rgba(4, 47, 49, 0.55);
  background: rgba(4, 67, 70, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  padding: 8px 22px;
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
}

.search-card {
  --home-search-radius: 22px;
  --home-search-inset: 8px;
  --home-search-inner-radius: calc(var(--home-search-radius) - var(--home-search-inset));
  background: rgba(255, 255, 255, 0.92) !important;
  backdrop-filter: blur(20px) saturate(160%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
  border: 1px solid rgba(255, 255, 255, 0.70) !important;
  border-radius: var(--home-search-radius) !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.18), 0 2px 8px rgba(0, 0, 0, 0.10) !important;
  overflow: hidden;
}

.search-card :deep(.v-field) {
  border-radius: var(--home-search-inner-radius) !important;
  overflow: hidden;
}

.search-card :deep(.v-field__overlay),
.search-card :deep(.v-field__outline),
.search-card :deep(.v-field__loader) {
  border-radius: inherit !important;
}

.search-card :deep(.v-btn) {
  border-radius: var(--home-search-inner-radius) !important;
}

.home-field-selector {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.home-field-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(15, 23, 42, 0.76);
  border-radius: 999px;
  background: transparent;
  color: #1e293b;
  cursor: pointer;
  font-family: var(--aa-font-sans);
  font-size: 0.88rem;
  font-weight: 600;
  line-height: 1;
  transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
}

.home-field-chip:hover,
.home-field-chip--active {
  border-color: #0D7377;
  background: rgba(13, 115, 119, 0.10);
  color: #0D7377;
}

/* ── Section Eyebrow ──────────────────────────────────────── */
.section-eyebrow {
  display: inline-block;
  font-size: 0.80rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: #0D7377;
  padding: 4px 14px;
  background: rgba(13, 115, 119, 0.09);
  border-radius: 20px;
  border: 1px solid rgba(13, 115, 119, 0.18);
}

/* ── Info Section Redesign ────────────────────────────────── */
.info-section {
  background: rgb(var(--v-theme-background));
  position: relative;
}

/* Glassmorphism Cards */
.apa-diagram-card, .why-mini-card {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.why-mini-card:hover, .apa-diagram-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.09);
}

/* Diagram Specifics */
.diagram-legend {
  display: flex;
  gap: 16px;
  font-size: 0.75rem;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-color-box {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.bg-teal-gradient { background: linear-gradient(135deg, #0D7377, #14919B); }
.bg-utr-gradient { background: linear-gradient(90deg, #B63F5A, #C9821A); }

.diagram-track-container {
  position: relative;
  padding-left: 12px;
  border-left: 2px dashed rgba(13, 115, 119, 0.2);
}

.diagram-visual {
  display: flex;
  align-items: center;
  position: relative;
  height: 24px;
  margin-right: 12px;
}

.diagram-spine {
  width: 12px;
  height: 2px;
  background: rgba(13, 115, 119, 0.5);
  margin-left: -12px;
}

.diagram-exon {
  height: 16px;
  width:62px;
  background: linear-gradient(135deg, #0D7377, #14919B);
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(13, 115, 119, 0.2);
  z-index: 2;
}

.diagram-intron {
  height: 2px;
  width: 32px;
  background: #14919B;
}

.diagram-utr {
  height: 10px;
  background: linear-gradient(90deg, #B63F5A, #C9821A);
  border-radius: 0 4px 4px 0;
  box-shadow: 0 2px 4px rgba(233, 69, 96, 0.2);
  z-index: 1;
}

.diagram-utr.short { width: 56px; }
.diagram-utr.long { width: 168px; }

.diagram-pas-marker {
  color: #B63F5A;
  font-size: 14px;
  margin-left: 2px;
  margin-top: -12px;
  text-shadow: 0 2px 4px rgba(233, 69, 96, 0.3);
}

.diagram-note {
  border-top: 1px solid rgba(13, 115, 119, 0.18);
}

/* 6.4/12 = 53.33% — fractional column width for the diagram panel */
@media (min-width: 1280px) {
  .col-diagram {
    flex: 0 0 53.33%;
    max-width: 53.33%;
  }
  .col-why {
    flex: 0 0 46.67%;
    max-width: 46.67%;
  }
}

@media (max-width: 960px) {
  .hero-section {
    min-height: 470px;
  }

  .hero-content {
    padding: 44px 0 52px;
  }

  .apa-diagram-card .d-flex.justify-space-between {
    align-items: flex-start !important;
    flex-direction: column;
    gap: 12px;
  }

  .diagram-legend {
    flex-wrap: wrap;
  }

  .diagram-track .d-flex.align-center {
    gap: 12px;
  }

  .diagram-visual {
    display: grid;
    grid-template-columns: 10px minmax(34px, 1.15fr) minmax(18px, 0.62fr) minmax(34px, 1.15fr) minmax(18px, 0.62fr) minmax(34px, 1.15fr) minmax(44px, 1.85fr) 12px;
    align-items: center;
    column-gap: 0;
    width: min(100%, 640px);
    max-width: 100%;
    flex: 1 1 auto;
    min-width: 0;
    margin-right: 0;
  }

  .diagram-spine {
    grid-column: 1;
    width: 100%;
  }

  .diagram-exon {
    width: 100%;
    min-width: 28px;
  }

  .diagram-intron {
    width: 100%;
    min-width: 16px;
  }

  .diagram-utr.short {
    width: clamp(30px, 42%, 58px);
    min-width: 0;
  }

  .diagram-utr.long {
    width: 100%;
    min-width: 0;
  }

  .diagram-pas-marker {
    justify-self: start;
  }

  .diagram-utr.short + .diagram-pas-marker {
    grid-column: 7;
    margin-left: clamp(32px, 42%, 58px);
  }

  .diagram-utr.long + .diagram-pas-marker {
    grid-column: 8;
    margin-left: 2px;
  }
}

@media (max-width: 640px) {
  .hero-section {
    min-height: 440px;
  }

  .hero-content {
    padding: 34px 0 42px;
  }

  .hero-content :deep(.text-h2) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 2.35rem !important;
  }

  .hero-subtitle {
    border-radius: 18px;
    padding: 8px 14px;
    font-size: 1.05rem;
  }

  .search-card :deep(.v-card-actions) {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
    padding-left: 12px !important;
    padding-right: 12px !important;
  }

  .home-field-selector {
    justify-content: center;
    width: 100%;
  }

  .search-card :deep(.v-btn) {
    width: 100%;
  }

  .diagram-track .d-flex.align-center {
    align-items: flex-start !important;
    flex-direction: column;
    gap: 10px;
  }

  .diagram-visual {
    width: 100%;
  }

  .diagram-track {
    padding-bottom: 4px;
  }
}

</style>
