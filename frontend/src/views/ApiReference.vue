<template>
  <div class="api-reference-page">
    <section class="api-hero">
      <div class="api-hero-bg"></div>
      <v-container class="api-hero-content">
        <div class="api-hero-kicker">Developer Resources</div>
        <h1>IsoAPA API Reference</h1>
        <p>
          A versioned, read-only REST interface for programmatic search, retrieval,
          statistics, and filtered data export.
        </p>
      </v-container>
    </section>

    <v-container class="api-content py-12">
      <section class="api-intro-grid">
        <article class="api-overview-card">
          <div class="api-card-icon"><v-icon icon="mdi-api" size="24" /></div>
          <div>
            <div class="api-label">Base URL</div>
            <code>{{ baseUrl }}</code>
            <p>All public endpoints use HTTP GET and return JSON unless a download format is requested.</p>
          </div>
        </article>
        <article class="api-overview-card">
          <div class="api-card-icon"><v-icon icon="mdi-shield-check-outline" size="24" /></div>
          <div>
            <div class="api-label">Access</div>
            <strong>No authentication required</strong>
            <p>Requests are rate-limited. Clients should handle HTTP 429 responses and avoid unnecessary polling.</p>
          </div>
        </article>
        <article class="api-overview-card">
          <div class="api-card-icon"><v-icon icon="mdi-package-variant-closed" size="24" /></div>
          <div>
            <div class="api-label">Complete species data</div>
            <router-link to="/download#bulk-species" class="api-inline-link">Use versioned bulk packages</router-link>
            <p>Precomputed archives are preferred for complete species-level exports.</p>
          </div>
        </article>
      </section>

      <section class="api-note-card">
        <div>
          <v-icon icon="mdi-ruler-square" size="20" />
          <strong>Conventions</strong>
        </div>
        <p>
          Species filters use stable identifiers such as <code>Human</code>, as returned by
          <code>/species</code>. JSON and TSV genomic positions are 1-based; BED files use 0-based,
          half-open coordinates. Transcript identifiers should include the version suffix when available.
        </p>
        <details class="api-count-conventions">
          <summary>Counting units</summary>
          <dl>
            <template v-for="entry in countConventions" :key="entry.field">
              <dt>{{ entry.field }}</dt>
              <dd>{{ entry.definition.text }}</dd>
            </template>
          </dl>
        </details>
      </section>

      <nav class="api-section-nav" aria-label="API reference sections">
        <a v-for="group in endpointGroups" :key="group.id" :href="`#${group.id}`">{{ group.title }}</a>
        <a href="#examples">Examples</a>
        <a href="#bulk-releases">Bulk releases</a>
      </nav>

      <section v-for="group in endpointGroups" :id="group.id" :key="group.id" class="api-section">
        <div class="api-section-heading">
          <div class="api-section-icon"><v-icon :icon="group.icon" size="22" /></div>
          <div>
            <div class="api-label">Public endpoints</div>
            <h2>{{ group.title }}</h2>
            <p>{{ group.description }}</p>
          </div>
        </div>

        <div class="endpoint-list">
          <article v-for="endpoint in group.endpoints" :key="endpoint.path" class="endpoint-card">
            <div class="endpoint-header">
              <span class="method-badge">GET</span>
              <code class="endpoint-path">{{ endpoint.path }}</code>
            </div>
            <p class="endpoint-summary">{{ endpoint.summary }}</p>

            <div v-if="endpoint.parameters?.length" class="parameter-table-wrap">
              <table class="parameter-table">
                <thead>
                  <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
                </thead>
                <tbody>
                  <tr v-for="parameter in endpoint.parameters" :key="parameter.name">
                    <td><code>{{ parameter.name }}</code></td>
                    <td>{{ parameter.type }}</td>
                    <td>{{ parameter.required ? 'Yes' : 'No' }}</td>
                    <td>{{ parameter.description }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="no-parameters">No parameters.</div>
          </article>
        </div>
      </section>

      <section id="examples" class="api-section">
        <div class="api-section-heading">
          <div class="api-section-icon"><v-icon icon="mdi-code-tags" size="22" /></div>
          <div>
            <div class="api-label">Ready to run</div>
            <h2>Examples</h2>
            <p>Examples use the current site origin, so they remain valid after deployment under another domain.</p>
          </div>
        </div>

        <div class="example-grid">
          <article v-for="example in examples" :key="example.title" class="example-card">
            <div class="example-card-header">
              <div>
                <span>{{ example.language }}</span>
                <h3>{{ example.title }}</h3>
              </div>
              <button type="button" class="copy-example" @click="copyExample(example)">
                <v-icon :icon="copiedTitle === example.title ? 'mdi-check' : 'mdi-content-copy'" size="17" />
                {{ copiedTitle === example.title ? 'Copied' : 'Copy' }}
              </button>
            </div>
            <pre><code>{{ example.code }}</code></pre>
          </article>
        </div>
      </section>

      <section id="bulk-releases" class="api-section">
        <div class="api-section-heading">
          <div class="api-section-icon"><v-icon icon="mdi-archive-arrow-down-outline" size="22" /></div>
          <div>
            <div class="api-label">Reproducible export</div>
            <h2>Bulk release files</h2>
            <p>Each archive contains PAS annotations, sample observations, BED6 coordinates, release metadata and a SHA256SUMS file. A separate checksum verifies the complete ZIP.</p>
          </div>
        </div>

        <div class="bulk-reference-card">
          <div class="bulk-reference-row">
            <span>Latest release pointer</span>
            <code>{{ origin }}/releases/latest.json</code>
          </div>
          <div class="bulk-reference-row">
            <span>Version manifest</span>
            <code>{{ origin }}/releases/&lt;version&gt;/manifest.json</code>
          </div>
          <div class="bulk-reference-row">
            <span>Archive naming</span>
            <code>IsoAPA_&lt;Species&gt;_v&lt;release&gt;.zip</code>
          </div>
          <div class="bulk-reference-row">
            <span>Verify extracted files</span>
            <code>sha256sum -c SHA256SUMS</code>
          </div>
          <router-link to="/download#bulk-species" class="bulk-reference-action">
            Browse species packages
            <v-icon icon="mdi-arrow-right" size="18" />
          </router-link>
        </div>
      </section>
    </v-container>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { COUNT_TERMS } from '@/constants/countingTerms'

const countConventions = [
  { field: 'Statistics: total_apa_sites', definition: COUNT_TERMS.pasClusters },
  { field: 'Release manifest: pa_site_count', definition: COUNT_TERMS.transcriptPasRecords },
  { field: 'Release manifest: observation_count', definition: COUNT_TERMS.sampleObservations },
  { field: 'Samples: total_samples / sample_count', definition: COUNT_TERMS.sampleGroups },
  { field: 'Statistics: avg_apa_per_transcript', definition: COUNT_TERMS.meanPas }
]

const copiedTitle = ref('')
const origin = computed(() => {
  if (typeof window === 'undefined' || !window.location?.origin) return 'https://isoapa.sls.cuhk.edu.hk'
  return window.location.origin
})
const baseUrl = computed(() => `${origin.value}/api/v1`)

const commonSpecies = {
  name: 'species',
  type: 'string',
  required: false,
  description: 'Stable identifier returned by /species. Search also accepts scientific and curated common names, such as Homo sapiens, human, Zea mays, or maize.'
}

const endpointGroups = [
  {
    id: 'discovery',
    title: 'Discovery and metadata',
    icon: 'mdi-database-search-outline',
    description: 'Discover valid filters and retrieve paginated transcript-level search results.',
    endpoints: [
      {
        path: '/api/v1/species',
        summary: 'List species identifiers, display names, scientific names, and genome assemblies.'
      },
      {
        path: '/api/v1/samples',
        summary: 'List sample groups, optionally restricted to one species.',
        parameters: [commonSpecies]
      },
      {
        path: '/api/v1/search',
        summary: 'Search transcript records. Exact and prefix gene-name matches are ranked before partial matches.',
        parameters: [
          { name: 'gene_name', type: 'string', required: false, description: 'Gene symbol or partial gene name.' },
          { name: 'transcript_id', type: 'string', required: false, description: 'Full or partial transcript identifier.' },
          { name: 'gene_id', type: 'string', required: false, description: 'Source gene identifier.' },
          { name: 'sample', type: 'string', required: false, description: 'Sample label; underscore and space variants are accepted.' },
          commonSpecies,
          { name: 'chromosome', type: 'string', required: false, description: 'Chromosome identifier.' },
          { name: 'sort_by', type: 'string', required: false, description: 'gene_name, transcript_id, chromosome, strand, apa_site_count, or species.' },
          { name: 'sort_desc', type: 'boolean', required: false, description: 'Set true for descending order.' },
          { name: 'page', type: 'integer', required: false, description: '1-based page number. Default: 1.' },
          { name: 'limit', type: 'integer', required: false, description: 'Records per page, 1-100. Default: 50.' }
        ]
      },
      {
        path: '/api/v1/autocomplete',
        summary: 'Return ranked suggestions for public search fields.',
        parameters: [
          { name: 'q', type: 'string', required: true, description: 'Search text; at least one character.' },
          { name: 'field', type: 'string', required: false, description: 'gene_name, gene_id, transcript_id, sample, or species.' },
          { name: 'limit', type: 'integer', required: false, description: 'Maximum suggestions, 1-50. Default: 10.' }
        ]
      }
    ]
  },
  {
    id: 'records',
    title: 'Gene and transcript records',
    icon: 'mdi-dna',
    description: 'Retrieve locus annotations while preserving the species and transcript context of each PA site.',
    endpoints: [
      {
        path: '/api/v1/transcript/{transcript_id}',
        summary: 'Return a transcript, its gene, unified PA sites, supporting samples, motif annotations, and abundance values.',
        parameters: [
          { name: 'transcript_id', type: 'path string', required: true, description: 'Public transcript identifier.' },
          commonSpecies
        ]
      },
      {
        path: '/api/v1/transcript/{transcript_id}/structure',
        summary: 'Return exon, CDS, and UTR coordinates used by the genome browser.',
        parameters: [
          { name: 'transcript_id', type: 'path string', required: true, description: 'Public transcript identifier.' },
          commonSpecies
        ]
      },
      {
        path: '/api/v1/transcript/{transcript_id}/site-sequence/{site_id}',
        summary: 'Return local sequence context for a PA site assigned to a transcript.',
        parameters: [
          { name: 'transcript_id', type: 'path string', required: true, description: 'Public transcript identifier.' },
          { name: 'site_id', type: 'path string', required: true, description: 'Unified PA-site identifier returned by the transcript endpoint.' },
          commonSpecies
        ]
      },
      {
        path: '/api/v1/gene/{gene_db_id}',
        summary: 'Return the gene-level summary and its transcript-resolved PA-site records.',
        parameters: [
          { name: 'gene_db_id', type: 'path integer', required: true, description: 'Release-specific database ID returned in /search results.' },
          commonSpecies
        ]
      },
      {
        path: '/api/v1/gene/{gene_db_id}/summary',
        summary: 'Return a species-aware external gene summary when one is available from MyGene.info.',
        parameters: [
          { name: 'gene_db_id', type: 'path integer', required: true, description: 'Release-specific database ID returned in /search results.' },
          commonSpecies
        ]
      }
    ]
  },
  {
    id: 'comparative',
    title: 'Cross-species comparison',
    icon: 'mdi-vector-link',
    description: 'Discover curated ortholog relationships and compare transcript-linked PA-site architecture and usage across species.',
    endpoints: [
      {
        path: '/api/v1/orthologs/search',
        summary: 'Search genes with ortholog mappings in a selected source species.',
        parameters: [
          { name: 'species', type: 'string', required: true, description: 'Source species identifier, scientific name, or supported common name.' },
          { name: 'q', type: 'string', required: true, description: 'Gene symbol or NCBI GeneID.' },
          { name: 'limit', type: 'integer', required: false, description: 'Maximum matches, 1-50. Default: 20.' }
        ]
      },
      {
        path: '/api/v1/orthologs/{gene_db_id}',
        summary: 'Return direct NCBI Gene orthologs represented in IsoAPA with per-gene PA-site summaries.',
        parameters: [
          { name: 'gene_db_id', type: 'path integer', required: true, description: 'Release-specific database gene ID.' }
        ]
      },
      {
        path: '/api/v1/orthologs/compare',
        summary: 'Return complete gene-level PAS profiles in genes[].sites and individual transcript profiles in genes[].transcripts. Gene usage pools supporting reads across all transcripts within each sample group. mean_abundance averages per-group fractions over groups supporting that PAS; missing calls are not measured zeros.',
        parameters: [
          { name: 'gene_ids', type: 'comma-separated integers', required: true, description: 'One to eight database gene IDs; every additional gene must be a direct ortholog of the first.' },
          { name: 'max_transcripts', type: 'integer', required: false, description: 'Maximum transcript profiles displayed per gene, 1-30. Default: 12. Gene-level sites and usage always include all transcripts.' }
        ]
      }
    ]
  },
  {
    id: 'statistics',
    title: 'Database statistics',
    icon: 'mdi-chart-box-outline',
    description: 'Retrieve database-scale summaries used by the Statistics page.',
    endpoints: [
      { path: '/api/v1/stats', summary: 'Return headline database counts and summary distributions.' },
      { path: '/api/v1/stats/detailed', summary: 'Return precomputed detailed database metrics.' },
      { path: '/api/v1/stats/multiplicity', summary: COUNT_TERMS.multiplicity.text, parameters: [commonSpecies] },
      { path: '/api/v1/stats/pas-motifs', summary: 'Return lineage-aware PAS motif counts for all data or one assessed species.', parameters: [commonSpecies] },
      { path: '/api/v1/stats/top-genes', summary: 'Return genes ranked by unique PAS cluster count, deduplicated across transcripts and sample groups.', parameters: [commonSpecies] },
      {
        path: '/api/v1/stats/pas-evidence',
        summary: 'Return unique PAS-cluster counts and percentages for PAS-L1, PAS-L2 and PAS-L3, sample-group count, motif-model assessment and reasons why PAS-L1 is unavailable. Counts are deduplicated across transcripts.',
        parameters: [{ name: 'species', type: 'string', required: true, description: 'Exact species identifier returned by /species, such as Human.' }]
      }
    ]
  },
  {
    id: 'downloads',
    title: 'Filtered downloads',
    icon: 'mdi-download-outline',
    description: 'Generate filtered exports interactively. Use bulk release files for complete species datasets.',
    endpoints: [
      {
        path: '/api/v1/download/apa-sites',
        summary: 'Download sample observations as CSV or TSV: one record for a transcript-associated PAS in a sample group.',
        parameters: [
          commonSpecies,
          { name: 'sample', type: 'repeatable string', required: false, description: 'Repeat this parameter to include multiple sample groups.' },
          { name: 'gene_name', type: 'string', required: false, description: 'Restrict output to matching gene names.' },
          { name: 'format', type: 'string', required: false, description: 'csv, tsv, or txt. Default: csv.' }
        ]
      },
      {
        path: '/api/v1/download/bed',
        summary: 'Download representative PA-site coordinates in BED6 format.',
        parameters: [commonSpecies]
      },
      {
        path: '/api/v1/download/genes',
        summary: 'Download gene-level identifiers, coordinates, transcript counts, and PA-site counts.',
        parameters: [
          commonSpecies,
          { name: 'format', type: 'string', required: false, description: 'csv, tsv, or txt. Default: csv.' }
        ]
      },
      {
        path: '/api/v1/download/transcripts',
        summary: 'Download transcript identifiers, genomic context, and PA-site counts.',
        parameters: [
          commonSpecies,
          { name: 'format', type: 'string', required: false, description: 'csv, tsv, or txt. Default: csv.' }
        ]
      },
      {
        path: '/api/v1/download/abundance-matrix',
        summary: COUNT_TERMS.abundanceMatrix.text,
        parameters: [
          commonSpecies,
          { name: 'sample', type: 'repeatable string', required: false, description: 'Repeat this parameter to include multiple sample groups.' },
          { name: 'format', type: 'string', required: false, description: 'tsv or csv. Default: tsv.' }
        ]
      }
    ]
  }
]

const examples = computed(() => [
  {
    language: 'cURL',
    title: 'Search human TP53 transcripts',
    code: `curl -fsS "${baseUrl.value}/search?gene_name=TP53&species=Human&page=1&limit=20"`
  },
  {
    language: 'Python',
    title: 'Retrieve a transcript record',
    code: `import requests\n\nurl = "${baseUrl.value}/transcript/NM_001101.5"\nresponse = requests.get(url, params={"species": "Human"}, timeout=30)\nresponse.raise_for_status()\nrecord = response.json()`
  },
  {
    language: 'cURL',
    title: 'Download filtered PA-site records',
    code: `curl -fL -o "ACTB_PA_sites.tsv" \\\n  "${baseUrl.value}/download/apa-sites?species=Human&gene_name=ACTB&format=tsv"`
  },
  {
    language: 'cURL',
    title: 'Find orthologs for a gene',
    code: `curl -fsS "${baseUrl.value}/orthologs/search?species=Human&q=TP53"`
  },
  {
    language: 'cURL',
    title: 'Resolve the latest bulk release',
    code: `curl -fsS "${origin.value}/releases/latest.json"`
  }
])

const copyExample = async (example) => {
  try {
    await navigator.clipboard.writeText(example.code)
    copiedTitle.value = example.title
    window.setTimeout(() => {
      if (copiedTitle.value === example.title) copiedTitle.value = ''
    }, 1800)
  } catch (error) {
    console.error('Unable to copy API example:', error)
  }
}
</script>

<style scoped>
.api-reference-page {
  min-height: 100vh;
  background: #f8fafc;
  color: var(--aa-slate-800);
}

.api-hero {
  position: relative;
  min-height: 300px;
  display: flex;
  align-items: center;
  overflow: hidden;
}

.api-hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 76% 28%, rgba(111, 210, 203, 0.2), transparent 27%),
    linear-gradient(135deg, #073f43 0%, #0d7377 48%, #17304a 100%);
}

.api-hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.18;
  background-image: linear-gradient(rgba(255,255,255,0.09) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.09) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(to right, transparent, black 56%);
}

.api-hero-content {
  position: relative;
  z-index: 1;
  padding: 52px 24px 58px;
}

.api-hero-kicker,
.api-label {
  color: #14919b;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.api-hero-kicker {
  color: #91e0dc;
  margin-bottom: 10px;
}

.api-hero h1 {
  max-width: 780px;
  margin: 0 0 12px;
  color: #fff;
  font-size: clamp(2.2rem, 4vw, 3.2rem);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.02em;
}

.api-hero p {
  max-width: 760px;
  margin: 0;
  color: rgba(255,255,255,0.86);
  font-size: 1.08rem;
  line-height: 1.6;
}

.api-content {
  max-width: 1180px;
}

.api-intro-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.api-overview-card,
.api-note-card,
.endpoint-card,
.example-card,
.bulk-reference-card {
  background: #fff;
  border: 1px solid #dbe3ea;
  box-shadow: none;
}

.api-overview-card {
  display: flex;
  gap: 14px;
  min-height: 158px;
  padding: 22px;
  border-radius: 18px;
}

.api-card-icon,
.api-section-icon {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  color: #0d7377;
  background: #effafa;
  border: 1px solid #cce8e6;
}

.api-card-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
}

.api-overview-card code,
.api-overview-card strong,
.api-inline-link {
  display: inline-block;
  margin-top: 7px;
  color: #1e293b;
  font-size: 0.9rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.api-inline-link {
  color: #0d7377;
  text-decoration: none;
  border-bottom: 1px solid rgba(13, 115, 119, 0.3);
}

.api-overview-card p {
  margin: 9px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.5;
}

.api-note-card {
  padding: 20px 24px;
  border-radius: 16px;
  border-left: 4px solid #14919b;
}

.api-note-card > div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0d7377;
}

.api-note-card p {
  margin: 7px 0 0;
  color: #475569;
  line-height: 1.65;
}

.api-note-card code,
.parameter-table code,
.bulk-reference-card code {
  color: #0a5c5f;
  font-family: var(--aa-font-mono);
  font-size: 0.82rem;
}

.api-count-conventions { margin-top: 14px; font-size: 0.88rem; }
.api-count-conventions summary { color: #0d7377; font-weight: 600; cursor: pointer; width: fit-content; }
.api-count-conventions dl { display: grid; grid-template-columns: minmax(180px, auto) 1fr; gap: 10px 24px; margin-top: 14px; line-height: 1.55; }
.api-count-conventions dt { color: #475569; font-weight: 600; }
.api-count-conventions dd { margin: 0; color: #64748b; }
@media (max-width: 640px) {
  .api-count-conventions dl { grid-template-columns: 1fr; gap: 4px; }
  .api-count-conventions dt:not(:first-child) { margin-top: 8px; }
}

.api-section-nav {
  position: sticky;
  z-index: 5;
  top: 68px;
  display: flex;
  gap: 8px;
  margin: 28px 0 44px;
  padding: 10px;
  overflow-x: auto;
  background: rgba(248, 250, 252, 0.94);
  border: 1px solid #dbe3ea;
  border-radius: 14px;
  backdrop-filter: blur(10px);
}

.api-section-nav a {
  flex: 0 0 auto;
  padding: 8px 12px;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  border-radius: 8px;
}

.api-section-nav a:hover {
  color: #0d7377;
  background: #effafa;
}

.api-section {
  scroll-margin-top: 136px;
  margin-bottom: 52px;
}

.api-section-heading {
  display: flex;
  gap: 15px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.api-section-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}

.api-section-heading h2 {
  margin: 3px 0 4px;
  color: #1e293b;
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.api-section-heading p {
  margin: 0;
  color: #64748b;
  line-height: 1.55;
}

.endpoint-list {
  display: grid;
  gap: 14px;
}

.endpoint-card {
  padding: 22px 24px;
  border-radius: 16px;
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 11px;
}

.method-badge {
  padding: 4px 8px;
  color: #0a5c5f;
  background: #dff5f4;
  border: 1px solid #b8e1df;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 800;
}

.endpoint-path {
  color: #1e293b;
  font-family: var(--aa-font-mono);
  font-size: 0.9rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.endpoint-summary {
  margin: 12px 0 16px;
  color: #475569;
  line-height: 1.6;
}

.parameter-table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.parameter-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.parameter-table th,
.parameter-table td {
  padding: 11px 13px;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid #edf2f6;
}

.parameter-table th {
  color: #64748b;
  background: #f8fafc;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.parameter-table td {
  color: #475569;
}

.parameter-table tbody tr:last-child td {
  border-bottom: 0;
}

.no-parameters {
  color: #94a3b8;
  font-size: 0.8rem;
}

.example-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.example-card {
  min-width: 0;
  overflow: hidden;
  border-radius: 16px;
}

.example-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 17px 18px;
}

.example-card-header span {
  color: #14919b;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.example-card h3 {
  margin: 2px 0 0;
  color: #334155;
  font-size: 0.94rem;
  font-weight: 650;
}

.example-card pre {
  min-height: 150px;
  margin: 0;
  padding: 20px;
  overflow-x: auto;
  color: #dbeafe;
  background: #0f172a;
  font-family: var(--aa-font-mono);
  font-size: 0.77rem;
  line-height: 1.65;
}

.copy-example {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 9px;
  color: #475569;
  background: #fff;
  border: 1px solid #dbe3ea;
  border-radius: 8px;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}

.copy-example:hover {
  color: #0d7377;
  border-color: #9bcfcb;
}

.bulk-reference-card {
  padding: 8px 24px 22px;
  border-radius: 16px;
}

.bulk-reference-row {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 18px;
  padding: 15px 0;
  border-bottom: 1px solid #edf2f6;
}

.bulk-reference-row span {
  color: #475569;
  font-weight: 600;
}

.bulk-reference-row code {
  overflow-wrap: anywhere;
}

.bulk-reference-action {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 20px;
  color: #0d7377;
  font-weight: 700;
  text-decoration: none;
}

@media (max-width: 900px) {
  .api-intro-grid,
  .example-grid {
    grid-template-columns: 1fr;
  }

  .api-overview-card {
    min-height: auto;
  }
}

@media (max-width: 640px) {
  .api-hero {
    min-height: 245px;
  }

  .api-hero-content {
    padding: 38px 18px 44px;
  }

  .api-hero p {
    font-size: 0.98rem;
  }

  .api-content {
    padding-right: 16px;
    padding-left: 16px;
  }

  .api-section-nav {
    top: 64px;
    margin-bottom: 36px;
  }

  .endpoint-card,
  .api-note-card,
  .bulk-reference-card {
    padding-right: 17px;
    padding-left: 17px;
  }

  .endpoint-header {
    align-items: flex-start;
  }

  .bulk-reference-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
