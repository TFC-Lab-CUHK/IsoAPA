<template>
  <div class="help-page">
    <!-- 1. Hero Section -->
    <section class="hero-section">
      <div class="hero-bg"></div>
      <v-container class="hero-content">
        <h1 class="text-h3 font-weight-bold text-white mb-2">User Guide & Documentation</h1>
        <p class="text-h6 text-white opacity-90">Everything you need to explore isoform-level APA data</p>
      </v-container>
    </section>

    <!-- Main Content -->
    <v-container class="py-12">
      <!-- 2. Jump Navigation Cards -->
      <div class="jump-nav-row">
        <div
          v-for="item in jumpLinks"
          :key="item.id"
          class="jump-card"
          @click="scrollTo(item.id)"
        >
          <div class="jump-card-icon" :style="{ background: item.gradient }">
            <v-icon :icon="item.icon" size="22" color="white"></v-icon>
          </div>
          <div>
            <div class="jump-card-title">{{ item.title }}</div>
            <div class="jump-card-desc">{{ item.sub }}</div>
          </div>
        </div>
      </div>

      <section class="workflow-card flat-card" aria-labelledby="apa-workflow-title">
        <div class="workflow-copy">
          <div class="section-eyebrow">Analysis Workflow</div>
          <h2 id="apa-workflow-title" class="workflow-title">How isoform-level PA sites are derived from long-read data</h2>
          <p class="workflow-desc">
            Filtered genome alignments of long reads are assigned to annotated transcripts. Their 3′ ends
            are clustered into PASs, screened for internal priming and unified across sample groups.
          </p>
        </div>
        <figure class="workflow-figure">
          <img
            src="/images/trek-workflow.png"
            width="3313"
            height="2208"
            alt="Workflow for deriving isoform-level polyadenylation sites from long-read sequencing data"
          >
        </figure>
      </section>

      <!-- 3. Quick Start Section -->
      <section id="getting-started" class="content-section">
        <div class="section-eyebrow">Quick Start</div>
        <h2 class="section-heading mb-6">Get up and running in 4 steps</h2>

        <div class="steps-grid">
          <div v-for="(step, index) in steps" :key="index" class="flat-card step-card">
            <div class="step-number">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="step-icon-badge" :style="{ background: step.gradient }">
              <v-icon :icon="step.icon" size="28" color="white"></v-icon>
            </div>
            <h3 class="step-title">{{ step.title }}</h3>
            <p class="step-desc">{{ step.desc }}</p>
            <v-btn v-if="step.link" :to="step.link" variant="tonal" color="#0D7377" class="mt-auto" rounded="pill" flat>
              {{ step.linkLabel }}
            </v-btn>
          </div>
        </div>
      </section>

      <!-- 4. Feature Guides Section -->
      <section id="features" class="content-section">
        <div class="section-eyebrow">Feature Guides</div>
        <h2 class="section-heading mb-6">How each feature works</h2>

        <div class="accordion-container">
          <div v-for="(guide, index) in guides" :key="index" class="flat-card accordion-item" :class="{ 'is-open': openGuide === index }">
            <button class="accordion-header" @click="openGuide = openGuide === index ? null : index">
              <div class="d-flex align-center">
                <div class="accordion-icon" :style="{ background: guide.gradient }">
                  <v-icon :icon="guide.icon" size="20" color="white"></v-icon>
                </div>
                <h3 class="accordion-title">{{ guide.title }}</h3>
              </div>
              <v-icon :icon="openGuide === index ? 'mdi-chevron-up' : 'mdi-chevron-down'" color="#64748b"></v-icon>
            </button>

            <div class="accordion-panel" :class="{ 'is-open': openGuide === index }">
              <div class="accordion-content">
                <!-- Guide 0 — Search & Filter -->
                <template v-if="index === 0">
                  <p class="guide-p">IsoAPA supports four search dimensions — combine any to narrow results.</p>
                  <div class="info-tiles-grid">
                    <div class="info-tile">
                      <div class="tile-title">Gene Name</div>
                      <div class="tile-desc">Enter a symbol (GAPDH, ACTB, ARF5). Partial matches are supported and autocomplete assists as you type.</div>
                    </div>
                    <div class="info-tile">
                      <div class="tile-title">Transcript ID</div>
                      <div class="tile-desc">Use a RefSeq transcript ID (for example, NM_001001186.4) for exact single-transcript lookup.</div>
                    </div>
                    <div class="info-tile">
                      <div class="tile-title">Tissue / Cell Line</div>
                      <div class="tile-desc">Filter by sample name (A549, Brain, Liver) to see sample-specific APA patterns.</div>
                    </div>
                    <div class="info-tile">
                      <div class="tile-title">Species</div>
                      <div class="tile-desc">Search by database identifier, scientific name or a common English name, then select the matching species to constrain the search scope.</div>
                    </div>
                  </div>
                  <div class="tip-box mt-4">
                    <v-icon icon="mdi-lightbulb-on-outline" color="#0D7377" class="mr-2"></v-icon>
                    <strong>Tip:</strong> The search bar on the home page supports live autocomplete — results appear as you type.
                  </div>
                </template>

                <!-- Guide 1 — Locus Detail View -->
                <template v-if="index === 1">
                  <p class="guide-p">Click any search result to open the full Locus Detail page for that transcript. The page is organised into three panels:</p>
                  <div class="guide-rows">
                    <div class="guide-row">
                      <v-icon icon="mdi-chart-gantt" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Genome Browser</strong> — Interactive diagram of the transcript's exon/intron/UTR structure with PA site markers overlaid. Hover a peak to see its position, supporting read count and relative usage for that transcript in the selected sample.</div>
                    </div>
                    <div class="guide-row">
                      <v-icon icon="mdi-table" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>PA Sites Details</strong> — Sortable table listing every polyadenylation site detected for the transcript, including cluster range, representative position, PAS motif, PAS evidence level, and mean transcript-level usage. Click any row to expand a colour-coded genomic sequence window centred on the cleavage site.</div>
                    </div>
                  </div>
                  <v-table density="compact" class="metrics-table mt-4">
                    <tbody>
                      <tr>
                        <td><strong>Site ID</strong></td>
                        <td class="text-grey-darken-1">Unified PAS cluster ID within a species; may be shared across transcripts and sample groups</td>
                      </tr>
                      <tr>
                        <td><strong>Cluster Range</strong></td>
                        <td class="text-grey-darken-1">Genomic span of the PA site cluster, formatted as start:end</td>
                      </tr>
                      <tr>
                        <td><strong>Rep. Position</strong></td>
                        <td class="text-grey-darken-1">Representative genomic coordinate of the unified PAS cluster</td>
                      </tr>
                      <tr>
                        <td><strong>PAS Motif</strong></td>
                        <td class="text-grey-darken-1">Lineage-appropriate primary or auxiliary PA signal detected in its expected positional window; unsupported species are marked as not assessed</td>
                      </tr>
                      <tr>
                        <td><strong>PAS Level</strong></td>
                        <td class="text-grey-darken-1">Evidence category assigned from cross-sample recurrence and a lineage-appropriate primary PAS motif</td>
                      </tr>
                      <tr>
                        <td><strong>Mean Abundance</strong></td>
                        <td class="text-grey-darken-1">Average transcript-level relative usage of this PA site across all samples in which it was detected</td>
                      </tr>
                    </tbody>
                  </v-table>
                  <div class="guide-rows mt-4">
                    <div class="guide-row">
                      <v-icon icon="mdi-view-grid-outline" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Per-site Abundance Heatmap</strong> — Sites × samples matrix. Colour intensity encodes relative abundance (0–100%); hatched cells indicate the site was not detected in that sample.</div>
                    </div>
                  </div>
                  <div class="tip-box mt-4">
                    <v-icon icon="mdi-lightbulb-on-outline" color="#0D7377" class="mr-2"></v-icon>
                    <strong>Tip:</strong> The transcript header shows biotype (mRNA, lncRNA, etc.), species name, and a direct link to the parent Gene Detail page.
                  </div>
                </template>

                <!-- Guide 2 — Gene Detail View -->
                <template v-if="index === 2">
                  <p class="guide-p">Click any gene name to open the Gene Detail page. The page is organised into three panels:</p>
                  <div class="guide-rows">
                    <div class="guide-row">
                      <v-icon icon="mdi-text-box-outline" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Gene Summary</strong> — Gene symbol, genomic location, species, and concise functional annotation.</div>
                    </div>
                    <div class="guide-row">
                      <v-icon icon="mdi-source-branch" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Transcripts and PA Sites</strong> — One row per transcript isoform. Expand a row to inspect the transcript-specific PA sites, PAS evidence level, abundance, and supporting samples.</div>
                    </div>
                  </div>
                  <v-table density="compact" class="metrics-table mt-4">
                    <tbody>
                      <tr>
                        <td><strong>Transcript</strong></td>
                        <td class="text-grey-darken-1">Transcript identifier; representative transcript badges are shown when a reference status is available</td>
                      </tr>
                      <tr>
                        <td><strong>Biotype</strong></td>
                        <td class="text-grey-darken-1">Transcript annotation class from the source reference</td>
                      </tr>
                      <tr>
                        <td><strong>PA Sites / Samples</strong></td>
                        <td class="text-grey-darken-1">Number of PA sites assigned to the transcript and the deduplicated samples supporting them</td>
                      </tr>
                      <tr>
                        <td><strong>Dominant PA Site</strong></td>
                        <td class="text-grey-darken-1">PA site with the broadest sample support for that transcript</td>
                      </tr>
                      <tr>
                        <td><strong>Expanded PA-site row</strong></td>
                        <td class="text-grey-darken-1">Shows Site ID, Cluster Range, Mean Abundance, PAS Level, and supporting sample names for each transcript-specific PA site</td>
                      </tr>
                    </tbody>
                  </v-table>
                  <div class="guide-rows mt-4">
                    <div class="guide-row">
                      <v-icon icon="mdi-fingerprint" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Isoform–APA Fingerprint</strong> — Visual summary of how PA sites distribute across isoforms. Extension segments indicate cases where PA evidence extends beyond the annotated terminal exon.</div>
                    </div>
                  </div>
                  <div class="tip-box mt-4">
                    <v-icon icon="mdi-lightbulb-on-outline" color="#0D7377" class="mr-2"></v-icon>
                    <strong>Tip:</strong> Click a transcript identifier to open its Locus Detail page, where the same PA sites are shown with genome-browser context, PAS motif details, sequence context, and the abundance heatmap.
                  </div>
                </template>

                <!-- Guide 3 — Statistics Dashboard -->
                <template v-if="index === 3">
                  <p class="guide-p">Statistics summarises observed transcripts, unique PAS clusters and sample groups. Selecting a species in any filter updates all four linked cards.</p>
                  <div class="guide-rows">
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>Sample groups</strong> — {{ COUNT_TERMS.sampleGroups.text }}</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>Mean PASs per isoform</strong> — {{ COUNT_TERMS.meanPas.text }}</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>PA Site Multiplicity</strong> — {{ COUNT_TERMS.multiplicity.text }}</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>PAS Motif Distribution</strong> — Pie chart summarising primary lineage-specific PA signals, auxiliary motifs, motif-absent sites, and species for which no validated model was applied.</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>PAS Evidence Levels</strong> — Select a species to view its sample coverage, motif model and evidence-level counts.</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>Species Richness</strong> — Species ranked by unique PAS cluster count.</div>
                    </div>
                    <div class="guide-row">
                      <div class="guide-row-bullet"></div>
                      <div><strong>Gene Richness</strong> — {{ COUNT_TERMS.genePasClusters.text }}</div>
                    </div>
                  </div>
                </template>

                <!-- Guide 4 — Download Options -->
                <template v-if="index === 4">
                  <p class="guide-p">Three distinct data products are available on the Download page.</p>
                  <div class="mini-cards-grid">
                    <div class="mini-card">
                      <div class="mini-card-title">PA Sites</div>
                      <div class="mini-card-desc">Per-sample transcript-PAS records with genomic positions and relative usage.</div>
                    </div>
                    <div class="mini-card">
                      <div class="mini-card-title">Genome Browser BED</div>
                      <div class="mini-card-desc">BED6 format — ready to load in IGV, UCSC Genome Browser, or JBrowse.</div>
                    </div>
                    <div class="mini-card">
                      <div class="mini-card-title">Sample Abundance Matrix</div>
                      <div class="mini-card-desc">{{ COUNT_TERMS.abundanceMatrix.text }}</div>
                    </div>
                  </div>
                  <p class="guide-p mt-4 text-body-2">
                    Use the species scope selector for filtered exports, or retrieve a versioned ZIP archive for a complete species dataset. The public API reference documents query parameters, coordinate conventions, response formats, and reproducible examples.
                  </p>
                  <div class="guide-resource-links">
                    <router-link to="/download#bulk-species">Browse species packages</router-link>
                    <router-link to="/api-reference">Open API reference</router-link>
                  </div>
                </template>

                <!-- Guide 5 - Cross-species Comparison -->
                <template v-if="index === 5">
                  <p class="guide-p">The Cross-species page compares PA-site architecture among genes connected by curated NCBI Gene ortholog relationships.</p>
                  <div class="guide-rows">
                    <div class="guide-row">
                      <v-icon icon="mdi-vector-link" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Select a source gene</strong> - Choose a species and search by gene symbol or GeneID. Only genes with a curated ortholog mapping are returned.</div>
                    </div>
                    <div class="guide-row">
                      <v-icon icon="mdi-select-group" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Choose orthologs</strong> - Compare up to eight genes, including one-to-many ortholog relationships where they occur.</div>
                    </div>
                    <div class="guide-row">
                      <v-icon icon="mdi-chart-timeline-variant" color="#355C7D" class="mr-3"></v-icon>
                      <div><strong>Inspect architecture and usage</strong> - Gene level pools PAS-supporting reads across all transcripts within each sample group. Transcript level retains each transcript's own relative usage. Select a sample group or the mean across groups supporting each site.</div>
                    </div>
                  </div>
                  <div class="tip-box mt-4">
                    <v-icon icon="mdi-information-outline" color="#0D7377" class="mr-2"></v-icon>
                    Distances share one scale, with each gene anchored at its own distal observed PAS. The view does not establish conservation between sites; sample coverage and annotations differ across species.
                  </div>
                </template>

              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 5. FAQ Section -->
      <section id="faq" class="content-section">
        <div class="section-eyebrow">FAQ</div>
        <h2 class="section-heading mb-6">Frequently asked questions</h2>

        <div class="accordion-container">
          <div v-for="(faq, index) in faqs" :key="index" class="flat-card faq-item">
            <button class="faq-header" @click="openFaq = openFaq === index ? null : index">
              <div class="faq-question">{{ faq.q }}</div>
              <div class="faq-icon-wrapper">
                <v-icon :icon="openFaq === index ? 'mdi-minus' : 'mdi-plus'" color="#14919B" size="20"></v-icon>
              </div>
            </button>
            <div class="accordion-panel" :class="{ 'is-open': openFaq === index }">
              <div class="faq-content">
                <p>{{ faq.a }}</p>
                <div v-if="faq.table" class="faq-table-wrap">
                  <table class="faq-table">
                    <thead>
                      <tr>
                        <th v-for="header in faq.table.headers" :key="header">{{ header }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="row in faq.table.rows" :key="row[0]">
                        <td v-for="(cell, cellIndex) in row" :key="`${row[0]}-${cellIndex}`">
                          {{ cell }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 6. Reference Sources Section -->
      <section id="references" class="content-section">
        <div class="section-eyebrow">Reference Sources</div>
        <h2 class="section-heading mb-3">Genome and annotation references</h2>
        <p class="reference-section-desc">
          Parent folders for the genome FASTA and transcript annotation resources used to construct IsoAPA.
        </p>

        <div class="flat-card reference-card" :class="{ 'is-open': referencesOpen }">
          <button class="reference-toggle" type="button" @click="referencesOpen = !referencesOpen">
            <div>
              <div class="reference-toggle-title">Reference source table</div>
              <div class="reference-toggle-subtitle">{{ referenceLinks.length }} species with verified source links</div>
            </div>
            <v-icon :icon="referencesOpen ? 'mdi-chevron-up' : 'mdi-chevron-down'" color="#64748b"></v-icon>
          </button>

          <div class="reference-panel" :class="{ 'is-open': referencesOpen }">
            <div class="reference-table-wrap">
              <table class="reference-table">
                <thead>
                  <tr>
                    <th>Species</th>
                    <th>Source</th>
                    <th>Annotation</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in referenceLinks" :key="row.species">
                    <td class="reference-species">{{ row.species }}</td>
                    <td>{{ row.source }}</td>
                    <td>
                      <div class="reference-link-stack">
                        <a
                          v-for="link in row.links"
                          :key="link.url"
                          :href="link.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="reference-link"
                        >
                          {{ link.label }}
                          <v-icon icon="mdi-open-in-new" size="13"></v-icon>
                        </a>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- 7. Glossary Section -->
      <section id="glossary" class="content-section">
        <div class="section-eyebrow">Glossary</div>
        <h2 class="section-heading mb-6">Key terms & definitions</h2>

        <div class="glossary-grid">
          <div v-for="(item, index) in glossary" :key="index" class="flat-card glossary-card">
            <div class="glossary-term">{{ item.term }}</div>
            <div class="glossary-desc">{{ item.desc }}</div>
          </div>
        </div>
      </section>

      <!-- 8. Contact Section -->
      <section id="contact" class="content-section">
        <div class="section-eyebrow">Contact</div>
        <h2 class="section-heading mb-6">Get in touch</h2>

        <div class="contact-card">
          <div class="contact-left">
            <h3 class="contact-heading">Questions or feedback?</h3>
            <p class="contact-sub">We welcome bug reports, feature requests, and general questions about IsoAPA.</p>
            <a href="mailto:tf.chan@cuhk.edu.hk" class="contact-email-btn">
              <v-icon icon="mdi-email-outline" size="20" class="mr-2"></v-icon>
              tf.chan@cuhk.edu.hk
            </a>
          </div>
          <div class="contact-right">
            <a
              class="contact-tile contact-tile-link"
              :href="bugIssueUrl"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Report a bug on GitHub"
            >
              <div class="contact-tile-icon"><v-icon icon="mdi-bug-outline" color="#0D7377"></v-icon></div>
              <div>
                <div class="contact-tile-title">
                  Report a Bug
                  <v-icon icon="mdi-open-in-new" size="14" class="contact-tile-link-icon"></v-icon>
                </div>
                <div class="contact-tile-desc">Found incorrect data or a broken feature? Send us details and we'll fix it.</div>
              </div>
            </a>
            <a
              class="contact-tile contact-tile-link"
              :href="featureIssueUrl"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Request a feature on GitHub"
            >
              <div class="contact-tile-icon"><v-icon icon="mdi-lightbulb-outline" color="#0D7377"></v-icon></div>
              <div>
                <div class="contact-tile-title">
                  Feature Request
                  <v-icon icon="mdi-open-in-new" size="14" class="contact-tile-link-icon"></v-icon>
                </div>
                <div class="contact-tile-desc">Suggest a new analysis type, species, or visualization.</div>
              </div>
            </a>
          </div>
        </div>
      </section>

    </v-container>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { referenceLinks } from '@/data/referenceLinks'
import { COUNT_TERMS } from '@/constants/countingTerms'

const route = useRoute()

const openGuide = ref(null)
const openFaq = ref(null)
const shouldOpenReferences = () => route.hash === '#references' || route.query.open === 'references'
const referencesOpen = ref(shouldOpenReferences())
const githubIssueBase = 'https://github.com/TFC-Lab-CUHK/IsoAPA/issues/new'
const bugIssueUrl = `${githubIssueBase}?title=Bug%3A%20`
const featureIssueUrl = `${githubIssueBase}?title=Feature%20request%3A%20`

const scrollTo = (id) => {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

watch(() => `${route.hash}:${route.query.open || ''}`, () => {
  if (shouldOpenReferences()) referencesOpen.value = true
})

const jumpLinks = [
  { id: 'getting-started', icon: 'mdi-rocket-launch', gradient: 'linear-gradient(135deg,#0D7377,#14919B)', title: 'Quick Start', sub: '4-step guide' },
  { id: 'features', icon: 'mdi-book-open-variant', gradient: 'linear-gradient(135deg,#355C7D,#4A7898)', title: 'Feature Guides', sub: 'Detailed how-tos' },
  { id: 'faq', icon: 'mdi-help-circle-outline', gradient: 'linear-gradient(135deg,#2E7D32,#388E3C)', title: 'FAQ', sub: 'Common questions' },
  { id: 'glossary', icon: 'mdi-book-alphabet', gradient: 'linear-gradient(135deg,#E65100,#EF6C00)', title: 'Glossary', sub: 'Key terms' }
]

const steps = [
  {
    icon: 'mdi-magnify',
    gradient: 'linear-gradient(135deg,#0D7377,#14919B)',
    title: 'Search for a Gene or Transcript',
    desc: 'Enter a gene symbol (GAPDH, ACTB) or RefSeq transcript ID. Autocomplete helps narrow your query.',
    link: '/search',
    linkLabel: 'Open Search'
  },
  {
    icon: 'mdi-table-eye',
    gradient: 'linear-gradient(135deg,#2E7D32,#388E3C)',
    title: 'Browse Results',
    desc: 'Scan the results table and click any row to open the full Locus Detail page for that transcript.',
    link: null,
    linkLabel: null
  },
  {
    icon: 'mdi-chart-bar',
    gradient: 'linear-gradient(135deg,#355C7D,#4A7898)',
    title: 'Inspect APA Sites',
    desc: 'Explore the genome browser, sample abundance charts, UTR composition, and RBP motif scanner.',
    link: null,
    linkLabel: null
  },
  {
    icon: 'mdi-download',
    gradient: 'linear-gradient(135deg,#E65100,#EF6C00)',
    title: 'Download Data',
    desc: 'Export PA sites as CSV/TSV, a BED genome track, or a sample abundance matrix for downstream analysis.',
    link: '/download',
    linkLabel: 'Go to Download'
  }
]

const guides = [
  { title: 'Search & Filter', icon: 'mdi-magnify', gradient: 'linear-gradient(135deg,#0D7377,#14919B)' },
  { title: 'Locus Detail View', icon: 'mdi-eye-outline', gradient: 'linear-gradient(135deg,#355C7D,#4A7898)' },
  { title: 'Gene Detail View', icon: 'mdi-dna', gradient: 'linear-gradient(135deg,#2E7D32,#388E3C)' },
  { title: 'Statistics Dashboard', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg,#AD1457,#E91E63)' },
  { title: 'Download Options', icon: 'mdi-download', gradient: 'linear-gradient(135deg,#E65100,#EF6C00)' },
  { title: 'Cross-species Comparison', icon: 'mdi-vector-link', gradient: 'linear-gradient(135deg,#0D7377,#355C7D)' }
]

const faqs = [
  {
    q: 'What is Alternative Polyadenylation (APA)?',
    a: 'APA is a post-transcriptional mechanism where the same pre-mRNA is cleaved and polyadenylated at different sites, producing isoforms with varying 3′ UTR lengths. This affects mRNA stability, translational efficiency, and sub-cellular localization.'
  },
  {
    q: 'What makes IsoAPA isoform-level?',
    a: 'IsoAPA calls PASs from long-read 3′ ends after assignment to annotated transcript models. Multi-exon reads require an exact match to the complete annotated intron chain. This preserves PAS usage within each reference transcript backbone; novel splice structures are not reconstructed.'
  },
  {
    q: 'What data sources are used?',
    a: 'IsoAPA integrates long-read transcriptomic data derived from Oxford Nanopore Technologies (ONT) cDNA and direct RNA sequencing, together with Pacific Biosciences (PacBio) Iso-Seq platforms. These datasets encompass a diverse collection of human and multi-species cell lines and tissues, enabling high-resolution, isoform-level identification of polyadenylation sites. Transcript coordinates are primarily based on NCBI/RefSeq annotations, supplemented by Ensembl or published annotations where required.'
  },
  {
    q: 'How is site abundance calculated?',
    a: 'Abundance = (reads at a specific PA site) ÷ (total reads at all PA sites for that transcript) × 100%. It represents the fractional usage of each cleavage site within a transcript in a given sample.'
  },
  {
    q: 'Why do PAS counts differ between Statistics and downloads?',
    a: 'Statistics counts unique PAS clusters; downloads also retain transcript associations and sample observations.',
    table: {
      headers: ['Counting unit', 'Definition'],
      rows: ['pasClusters', 'transcriptPasRecords', 'sampleObservations', 'sampleGroups'].map(key => [COUNT_TERMS[key].label, COUNT_TERMS[key].text])
    }
  },
  {
    q: 'What do PAS evidence levels mean?',
    a: 'PAS evidence levels combine recurrence across distinct sample groups with lineage-appropriate primary motif support. They summarise supporting evidence, not calibrated probabilities of correctness. Shared transcript records do not increase the sample-group count.',
    table: {
      headers: ['Level', 'Classification', 'Evidence summary'],
      rows: [
        ['PAS-L1', 'Convergent evidence', 'Detected in at least two sample groups, with primary motif support.'],
        ['PAS-L2', 'Additional support', 'Recurrence in at least two sample groups or primary motif support, but not both.'],
        ['PAS-L3', 'Baseline call', 'Retained PAS with neither additional evidence type documented.']
      ]
    }
  },
  {
    q: 'Can I use IsoAPA data in publications?',
    a: 'Yes. IsoAPA data is freely available for research and publication. Please cite our database when using it in your work.'
  },
  {
    q: 'How are genes matched across species?',
    a: 'IsoAPA uses curated NCBI Gene ortholog relationships. Gene symbols alone are not treated as evidence of orthology, and genes without a supported mapping are reported as unavailable.'
  },
  {
    q: 'What do \'proximal\' and \'distal\' PAS mean?',
    a: 'Proximal PAS is the polyadenylation site closest to the stop codon, producing a shorter 3′ UTR (UTR shortening). Distal PAS is farthest from the stop codon, producing a longer 3′ UTR (UTR lengthening). Cells dynamically shift between these under stress, development, or disease conditions.'
  }
]

const glossary = [
  { term: 'APA', desc: 'Alternative Polyadenylation — a mechanism producing multiple mRNA isoforms with different 3′ UTR lengths' },
  { term: 'PAS', desc: 'Polyadenylation site; nearby cleavage positions are grouped into a unified PAS cluster' },
  { term: '3′ UTR', desc: '3′ Untranslated Region — mRNA region downstream of the stop codon; regulates stability, translation, and localization' },
  { term: 'Proximal PAS', desc: 'Polyadenylation site closest to the coding region; its use produces shorter 3′ UTRs' },
  { term: 'Distal PAS', desc: 'Polyadenylation site farthest from the coding region; its use produces longer 3′ UTRs' },
  { term: 'Abundance', desc: 'Relative usage of an APA site as a fraction of all PA site reads for a given transcript in a sample' }
]
</script>

<style scoped>
.help-page {
  min-height: 100vh;
  background-color: #f8fafc;
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
@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
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

.section-eyebrow {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #14919B;
  margin-bottom: 4px;
}
.section-heading {
  font-size: 1.75rem;
  font-weight: 800;
  color: #1e293b;
}

.content-section {
  margin-bottom: 80px;
}

.flat-card {
  background: #fff;
  border: 1px solid rgba(203, 213, 225, 0.72);
  border-radius: 20px;
  box-shadow: none;
}

.jump-nav-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 80px;
}
@media (max-width: 960px) {
  .jump-nav-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .jump-nav-row { grid-template-columns: 1fr; }
}
.jump-card {
  background: rgba(255, 255, 255, 0.80);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 20px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  display: flex;
  align-items: center;
  gap: 16px;
}
.jump-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(13,115,119,0.12);
}
.jump-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.jump-card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 2px;
}
.jump-card-desc {
  font-size: 0.8rem;
  color: #64748b;
}

.workflow-card {
  padding: 28px;
  margin: -44px 0 80px;
}
.workflow-copy {
  margin-bottom: 22px;
}
.workflow-title {
  font-size: 1.55rem;
  font-weight: 800;
  color: #1e293b;
  line-height: 1.25;
  margin-bottom: 10px;
}
.workflow-desc {
  font-size: 0.96rem;
  line-height: 1.65;
  color: #475569;
  margin: 0;
}
.workflow-figure {
  margin: 0;
  background: transparent;
  overflow: hidden;
}
.workflow-figure img {
  display: block;
  width: 100%;
  height: auto;
}
@media (max-width: 768px) {
  .workflow-card {
    padding: 22px;
    margin-top: -48px;
  }
  .workflow-title {
    font-size: 1.32rem;
  }
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
@media (max-width: 1024px) {
  .steps-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .steps-grid { grid-template-columns: 1fr; }
}
.step-card {
  padding: 32px 24px 24px;
  position: relative;
  display: flex;
  flex-direction: column;
}
.step-number {
  position: absolute;
  top: 16px;
  right: 20px;
  font-size: 3.5rem;
  font-weight: 900;
  color: rgba(20, 145, 155, 0.08);
  line-height: 1;
}
.step-icon-badge {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.step-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 12px;
  line-height: 1.3;
}
.step-desc {
  font-size: 0.88rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 24px;
}

.accordion-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.accordion-item {
  transition: border-color 160ms ease;
  overflow: hidden;
}
.accordion-item.is-open {
  border-left: 3px solid #14919B;
}
.accordion-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}
.accordion-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.accordion-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}
.accordion-panel {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transform: translateY(-6px);
  transform-origin: top center;
  transition:
    max-height 320ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 180ms ease,
    transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
  will-change: max-height, opacity, transform;
}
.accordion-panel.is-open {
  max-height: 720px;
  opacity: 1;
  transform: translateY(0);
}
.accordion-panel > * {
  transform: translateY(-4px);
  transition: transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
}
.accordion-panel.is-open > * {
  transform: translateY(0);
}
.accordion-content {
  --guide-readable-width: 98%;
  padding: 0 24px 24px 76px;
}
@media (max-width: 600px) {
  .accordion-content { padding: 0 20px 20px 20px; }
}

.guide-p {
  max-width: var(--guide-readable-width);
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
  margin-bottom: 16px;
}
.info-tiles-grid {
  max-width: var(--guide-readable-width);
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
@media (max-width: 768px) {
  .info-tiles-grid { grid-template-columns: 1fr; }
}
.info-tile {
  background: rgba(248, 250, 252, 0.6);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 16px;
}
.tile-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
  font-size: 0.95rem;
}
.tile-desc {
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
}
.tip-box {
  max-width: var(--guide-readable-width);
  background: rgba(240, 253, 250, 0.8);
  border: 1px solid rgba(20, 145, 155, 0.2);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 0.9rem;
  color: #0f172a;
  display: flex;
  align-items: flex-start;
}
.guide-rows {
  max-width: var(--guide-readable-width);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.guide-row {
  display: flex;
  align-items: flex-start;
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.5;
}
.guide-row-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #14919B;
  margin-top: 8px;
  margin-right: 12px;
  flex-shrink: 0;
}
.guide-ul {
  padding-left: 24px;
  margin-bottom: 16px;
  color: #475569;
  font-size: 0.95rem;
  line-height: 1.6;
}
.guide-ul li { margin-bottom: 8px; }
.metrics-table {
  width: min(var(--guide-readable-width), 100%) !important;
  background: rgba(248, 250, 252, 0.5) !important;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
}
.metrics-table td {
  font-size: 0.85rem !important;
  border-bottom: 1px solid #f1f5f9 !important;
}
.metrics-table td:first-child {
  white-space: nowrap;
  width: 1%;
  padding-right: 24px !important;
}
.mini-cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 768px) {
  .mini-cards-grid { grid-template-columns: 1fr; }
}
.mini-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}
.mini-card-title {
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
  font-size: 0.95rem;
}
.mini-card-desc {
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
}

.guide-resource-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  max-width: var(--guide-readable-width);
}

.guide-resource-links a {
  padding: 8px 12px;
  color: #0d7377;
  background: #effafa;
  border: 1px solid #c9e7e5;
  border-radius: 9px;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
}

.guide-resource-links a:hover {
  color: #0a5c5f;
  border-color: #93c9c5;
}

.faq-item {
  overflow: hidden;
}
.faq-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}
.faq-question {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0D7377;
  padding-right: 16px;
}
.faq-icon-wrapper {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(20, 145, 155, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}
.faq-content {
  padding: 0 24px 20px 24px;
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
}

.faq-table-wrap {
  margin-top: 14px;
  overflow-x: auto;
  border: 1px solid rgba(203, 213, 225, 0.72);
  border-radius: 14px;
  background: #ffffff;
}

.faq-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 760px;
}

.faq-table th {
  padding: 11px 14px;
  background: #eef7f7;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(203, 213, 225, 0.72);
}

.faq-table td {
  padding: 12px 14px;
  color: #475569;
  font-size: 0.9rem;
  line-height: 1.55;
  vertical-align: top;
  border-bottom: 1px solid rgba(226, 232, 240, 0.82);
}

.faq-table tbody tr:last-child td {
  border-bottom: 0;
}

.faq-table td:first-child {
  color: #0D7377;
  font-weight: 800;
  white-space: nowrap;
}

.reference-section-desc {
  margin: 0 0 20px;
  color: #475569;
  font-size: 0.95rem;
  line-height: 1.65;
}
.reference-card {
  overflow: hidden;
}
.reference-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  background: transparent;
  border: 0;
  text-align: left;
  cursor: pointer;
}
.reference-toggle-title {
  color: #1e293b;
  font-size: 1.06rem;
  font-weight: 800;
  line-height: 1.3;
}
.reference-toggle-subtitle {
  color: #64748b;
  font-size: 0.86rem;
  margin-top: 3px;
}
.reference-panel {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transition:
    max-height 360ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 180ms ease;
}
.reference-panel.is-open {
  max-height: 940px;
  opacity: 1;
}
.reference-table-wrap {
  max-height: 720px;
  overflow: auto;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}
.reference-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 760px;
}
.reference-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-align: left;
  text-transform: uppercase;
  padding: 13px 18px;
  border-bottom: 1px solid rgba(203, 213, 225, 0.82);
}
.reference-table td {
  color: #475569;
  font-size: 0.88rem;
  padding: 13px 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.78);
  vertical-align: middle;
}
.reference-table tbody tr:hover td {
  background: rgba(13, 115, 119, 0.035);
}
.reference-species {
  color: #1e293b !important;
  font-weight: 700;
  white-space: nowrap;
}
.reference-link-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.reference-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #0D7377;
  background: rgba(13, 115, 119, 0.08);
  border: 1px solid rgba(13, 115, 119, 0.14);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
}
.reference-link:hover {
  background: rgba(13, 115, 119, 0.13);
  color: #0a5c5f;
}
.glossary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 960px) {
  .glossary-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .glossary-grid { grid-template-columns: 1fr; }
}
.glossary-card {
  padding: 20px;
}
.glossary-term {
  display: inline-block;
  background: rgba(20, 145, 155, 0.1);
  color: #0D7377;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 12px;
}
.glossary-desc {
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.5;
}

.contact-card {
  background: rgba(240, 253, 250, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 2px solid rgba(20, 145, 155, 0.25);
  border-radius: 20px;
  padding: 40px;
  display: flex;
  gap: 40px;
  align-items: center;
}
@media (max-width: 800px) {
  .contact-card { flex-direction: column; align-items: stretch; padding: 32px 24px; gap: 32px; }
}
.contact-left {
  flex: 1;
}
.contact-heading {
  font-size: 1.5rem;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 12px;
}
.contact-sub {
  font-size: 1rem;
  color: #475569;
  margin-bottom: 24px;
  line-height: 1.5;
}
.contact-email-btn {
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, #0D7377, #14919B);
  color: white !important;
  text-decoration: none;
  padding: 12px 24px;
  border-radius: 999px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(13, 115, 119, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;
}
.contact-email-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(13, 115, 119, 0.35);
}
.contact-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.contact-tile {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  border: 1px solid rgba(20, 145, 155, 0.15);
}
.contact-tile-link {
  color: inherit;
  text-decoration: none;
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease;
}
.contact-tile-link:hover {
  background: #fbfefd;
  border-color: rgba(20, 145, 155, 0.32);
  transform: translateY(-1px);
}
.contact-tile-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(20, 145, 155, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.contact-tile-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
  font-size: 1rem;
}
.contact-tile-link-icon {
  color: #64748b;
  opacity: 0.75;
}
.contact-tile-link:hover .contact-tile-title {
  color: #0D7377;
}
.contact-tile-link:hover .contact-tile-link-icon {
  color: #0D7377;
  opacity: 1;
}
.contact-tile-desc {
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.4;
}

@media (min-width: 641px) and (max-width: 1024px) {
  .hero-content {
    padding-left: 22px !important;
    padding-right: 22px !important;
  }
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

  .content-section {
    margin-bottom: 54px;
  }

  .jump-nav-row {
    gap: 12px;
    margin-bottom: 60px;
  }

  .workflow-card {
    padding: 18px;
    margin-bottom: 58px;
  }

  .workflow-figure {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .workflow-figure img {
    min-width: 760px;
  }

  .accordion-header {
    padding: 16px 18px;
  }

  .accordion-content,
  .faq-content {
    padding-left: 18px;
    padding-right: 18px;
  }

  .reference-toggle {
    align-items: flex-start;
    padding: 16px 18px;
  }

  .contact-card {
    padding: 24px 18px;
  }

  .contact-email-btn {
    justify-content: center;
    width: 100%;
    padding-left: 14px;
    padding-right: 14px;
  }
}
</style>
