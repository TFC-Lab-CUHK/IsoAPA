<template>
  <div class="download-page">
    <!-- 1. Hero -->
    <section class="hero-section">
      <div class="hero-bg"></div>
      <v-container class="hero-content">
        <h1 class="text-h3 font-weight-bold text-white mb-2">Download IsoAPA Data</h1>
        <p class="text-h6 text-white opacity-90">Export of isoform-level polyadenylation results</p>
      </v-container>
    </section>

    <!-- 2. Main content -->
    <v-container class="py-12">
      <!-- A. Dataset Cards -->
      <div class="section-eyebrow mb-2">Choose Dataset</div>
      <div class="dataset-cards-row mb-8">
        <div 
          v-for="item in datasets" 
          :key="item.id"
          class="dataset-card" 
          :class="{ 'dataset-card--selected': selectedDataset?.id === item.id }" 
          @click="selectDataset(item)"
        >
          <div class="dataset-card-icon" :style="{ background: item.gradient }">
            <v-icon :icon="item.icon" size="28" color="white"></v-icon>
          </div>
          <div class="dataset-card-title">{{ item.title }}</div>
          <div class="dataset-card-desc">{{ item.description }}</div>
          <div class="dataset-card-meta">
            <v-chip size="x-small" variant="tonal" color="primary">{{ item.countLabel }}</v-chip>
            <MetricHelp v-if="item.countDefinition" :definition="item.countDefinition" />
            <v-chip size="x-small" variant="outlined" class="ml-1" v-for="fmt in item.formats" :key="fmt">{{ fmt.toUpperCase() }}</v-chip>
          </div>
        </div>
      </div>

      <!-- B. Scope + Format -->
      <div class="section-eyebrow mb-2">Filter & Format</div>
      <div class="scope-panel">
        <div class="scope-group">
          <div class="scope-label">
            <v-icon icon="mdi-earth" size="16" class="mr-1"></v-icon>
            Species Scope
          </div>
          <div class="scope-chips-row">
            <button class="scope-chip" :class="{ active: !selectedSpecies }" @click="selectedSpecies = null">
              <v-icon icon="mdi-database" size="14" class="mr-1"></v-icon>
              Whole Dataset
            </button>
            <button
              v-for="sp in speciesList"
              :key="sp.id"
              class="scope-chip"
              :class="{ active: selectedSpecies === sp.name }"
              @click="selectedSpecies = sp.name"
            >
              {{ formatSpeciesName(sp) }}
              <span class="scope-chip-latin" v-if="formatSpeciesSubtitle(sp)">{{ formatSpeciesSubtitle(sp) }}</span>
            </button>
          </div>
        </div>

        <div class="scope-divider"></div>

        <div class="scope-group scope-group--samples" v-if="sampleFilterEnabled">
          <div class="scope-label">
            <v-icon icon="mdi-flask-outline" size="16" class="mr-1"></v-icon>
            Samples
            <span class="scope-label-hint">{{ selectedSamples.length }} selected</span>
          </div>
          <v-autocomplete
            v-model="selectedSamples"
            :items="filteredSampleOptions"
            item-title="title"
            item-value="value"
            multiple
            clearable
            chips
            closable-chips
            density="compact"
            variant="outlined"
            hide-details
            class="sample-multi-select"
            menu-icon="mdi-chevron-down"
            :menu-props="{ contentClass: 'sample-select-menu' }"
            placeholder="All samples"
            no-data-text="No samples available"
          >
            <template #chip="{ props, item }">
              <v-chip v-bind="props" size="small" class="sample-select-chip">
                {{ item.raw.title }}
              </v-chip>
            </template>
            <template #item="{ props, item }">
              <v-list-item v-bind="props" :title="item.raw.title"></v-list-item>
            </template>
          </v-autocomplete>
        </div>

        <div class="scope-divider scope-divider--format" v-if="sampleFilterEnabled"></div>

        <div class="scope-group scope-group--format">
          <div class="scope-label">
            <v-icon icon="mdi-file-delimited" size="16" class="mr-1"></v-icon>
            Format
          </div>
          <div class="scope-chips-row">
            <template v-if="selectedDataset && selectedDataset.formats.length === 1">
              <button class="scope-chip active" style="cursor:default;">
                {{ selectedDataset.formats[0].toUpperCase() }}
              </button>
            </template>
            <template v-else>
              <button
                v-for="fmt in (selectedDataset ? selectedDataset.formats : ['csv','tsv'])"
                :key="fmt"
                class="scope-chip"
                :class="{ active: selectedFormat === fmt }"
                @click="selectedFormat = fmt"
              >
                {{ fmt.toUpperCase() }}
              </button>
            </template>
          </div>
        </div>
      </div>

      <!-- C. Download Action Panel -->
      <div v-if="selectedDataset" class="download-action-panel">
        <div class="download-action-info">
          <div class="download-action-eyebrow">Ready to Download</div>
          <div class="download-action-title">
            {{ selectedDataset.title }}
            <span v-if="selectedSpecies" class="download-action-species"> · {{ selectedSpeciesLabel }}</span>
            <span v-if="selectedSamples.length" class="download-action-species"> · {{ sampleSelectionLabel }}</span>
          </div>
          <div class="download-action-meta">
            <v-chip size="small" variant="tonal" color="primary" class="mr-2">{{ selectedFormat.toUpperCase() }}</v-chip>
          </div>
        </div>
        <v-btn
          size="x-large"
          class="download-btn"
          :loading="downloading"
          @click="triggerDownload"
        >
          <v-icon start icon="mdi-download"></v-icon>
          Download
        </v-btn>
      </div>

      <!-- D. Versioned per-species releases -->
      <section id="bulk-species" class="bulk-section">
        <div class="section-eyebrow mb-2">Bulk Species Downloads</div>
        <div class="bulk-card">
          <div class="bulk-card-header">
            <div>
              <div class="bulk-title-row">
                <h3 class="bulk-card-title">Versioned Species Packages</h3>
                <span v-if="bulkManifest" class="release-badge">v{{ bulkManifest.release }}</span>
              </div>
              <p class="bulk-card-subtitle">
                Precomputed, checksum-verified archives for complete species-level retrieval.
              </p>
            </div>
            <a
              v-if="bulkManifestUrl"
              :href="bulkManifestUrl"
              class="manifest-link"
              target="_blank"
              rel="noopener"
            >
              Release manifest
              <v-icon icon="mdi-open-in-new" size="16"></v-icon>
            </a>
          </div>

          <div v-if="bulkLoading" class="bulk-state">
            <v-progress-circular indeterminate size="22" width="2" color="primary"></v-progress-circular>
            Loading release manifest
          </div>
          <div v-else-if="bulkError" class="bulk-state bulk-state--error">
            <v-icon icon="mdi-alert-circle-outline" size="20"></v-icon>
            {{ bulkError }}
          </div>
          <template v-else-if="bulkManifest">
            <v-autocomplete
              v-model="selectedBulkSpecies"
              :items="bulkSpeciesOptions"
              item-title="title"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="bulk-species-select"
              menu-icon="mdi-chevron-down"
              placeholder="Select a species"
            ></v-autocomplete>

            <div v-if="selectedBulkPackage" class="bulk-package">
              <div class="bulk-package-main">
                <div class="bulk-package-icon"><v-icon icon="mdi-folder-zip-outline" size="25"></v-icon></div>
                <div>
                  <div class="bulk-package-name">{{ selectedBulkPackage.file_name }}</div>
                  <div class="bulk-package-meta">
                    <span class="bulk-count">{{ formatNumber(selectedBulkPackage.pa_site_count) }} Transcript-PAS records<MetricHelp :definition="COUNT_TERMS.transcriptPasRecords" /></span>
                    <i class="bulk-meta-separator" aria-hidden="true"></i>
                    <span class="bulk-count">{{ formatNumber(selectedBulkPackage.observation_count) }} sample observations<MetricHelp :definition="COUNT_TERMS.sampleObservations" /></span>
                    <i class="bulk-meta-separator" aria-hidden="true"></i>
                    {{ formatFileSize(selectedBulkPackage.size_bytes) }}
                  </div>
                </div>
              </div>
              <div class="bulk-package-actions">
                <a :href="selectedBulkPackage.url" class="bulk-download-btn" download>
                  <v-icon icon="mdi-download" size="19"></v-icon>
                  Download ZIP
                </a>
              </div>
            </div>

            <div class="bulk-contents">
              <span><v-icon icon="mdi-table" size="16"></v-icon> Transcript-PAS table</span>
              <span><v-icon icon="mdi-format-list-bulleted" size="16"></v-icon> Sample observations</span>
              <span><v-icon icon="mdi-dna" size="16"></v-icon> BED6 track</span>
              <span><v-icon icon="mdi-file-document-check-outline" size="16"></v-icon> Release metadata</span>
              <span title="SHA-256 checksums for the files inside the ZIP"><v-icon icon="mdi-shield-check-outline" size="16"></v-icon> SHA256SUMS</span>
            </div>
          </template>
        </div>
      </section>

      <!-- E. API Access -->
      <div class="section-eyebrow mb-2">Programmatic Access</div>
      <div class="api-card">
        <div class="api-card-header">
          <div>
            <h3 class="api-card-title">Download via API</h3>
            <p class="api-card-subtitle">Commands update automatically when you change the dataset or scope above.</p>
          </div>
          <router-link to="/api-reference" class="api-reference-link">
            API Reference
            <v-icon icon="mdi-arrow-right" size="17"></v-icon>
          </router-link>
        </div>

        <div class="lang-tabs">
          <button
            v-for="lang in ['curl','python','r']"
            :key="lang"
            class="lang-tab"
            :class="{ active: apiLang === lang }"
            @click="apiLang = lang"
          >
            {{ langLabel(lang) }}
          </button>
        </div>

        <div class="code-block">
          <pre class="code-text"><code>{{ currentCommand }}</code></pre>
          <button class="copy-btn" @click="copyCommand">
            <v-icon :icon="copied ? 'mdi-check' : 'mdi-content-copy'" size="18"></v-icon>
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
      </div>

      <!-- F. Schema (collapsed) -->
      <div class="schema-section">
        <div class="dense-view-note">
          Data schema tables can be scrolled horizontally on small screens.
        </div>
        <button class="schema-toggle-btn" @click="schemaOpen = !schemaOpen">
          <v-icon :icon="schemaOpen ? 'mdi-chevron-up' : 'mdi-chevron-down'" size="20" class="mr-2"></v-icon>
          {{ schemaOpen ? 'Hide Data Schema' : 'View Data Schema' }}
        </button>

        <div class="schema-panel" :class="{ 'is-open': schemaOpen }">
          <div class="schema-content mt-6">
            <div class="lang-tabs schema-tabs">
              <button 
                v-for="s in schemas" 
                :key="s.id" 
                class="lang-tab" 
                :class="{ active: schemaTab === s.id }" 
                @click="schemaTab = s.id"
              >
                {{ s.title }}
              </button>
            </div>
            <div class="schema-table-wrapper">
              <v-table density="compact" class="elegant-table">
                <thead>
                  <tr>
                    <th>Field</th><th>Type</th><th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="f in currentSchema" :key="f.name">
                    <td><code class="field-badge">{{ f.name }}</code></td>
                    <td><span class="type-badge">{{ f.type }}</span></td>
                    <td class="text-grey-darken-1">{{ f.desc }}</td>
                  </tr>
                </tbody>
              </v-table>
            </div>
          </div>
        </div>
      </div>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { apiService } from '@/services/api'
import { formatSampleName, formatSpeciesName, formatSpeciesSubtitle } from '@/utils/formatters'
import MetricHelp from '@/components/MetricHelp.vue'
import { COUNT_TERMS } from '@/constants/countingTerms'

const speciesList = ref([])
const sampleList = ref([])
const detailedStats = ref({})
const selectedDataset = ref(null)
const selectedSpecies = ref(null)
const selectedSamples = ref([])
const selectedFormat = ref('csv')
const apiLang = ref('curl')
const copied = ref(false)
const schemaOpen = ref(false)
const schemaTab = ref('apa-sites')
const downloading = ref(false)
const bulkManifest = ref(null)
const bulkManifestUrl = ref('')
const bulkLoading = ref(true)
const bulkError = ref('')
const selectedBulkSpecies = ref('Human')

const formatCompactCount = (value) => {
  const count = Number(value || 0)
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(count >= 10_000_000 ? 0 : 1)}M`
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`
  return count.toLocaleString()
}

const formatNumber = (value) => Number(value || 0).toLocaleString()

const formatFileSize = (value) => {
  const bytes = Number(value || 0)
  if (bytes >= 1024 ** 3) return `${(bytes / (1024 ** 3)).toFixed(2)} GB`
  if (bytes >= 1024 ** 2) return `${(bytes / (1024 ** 2)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}


const bulkSpeciesOptions = computed(() => (bulkManifest.value?.species || []).map(entry => ({
  title: entry.display_name || formatSpeciesName(entry.species),
  value: entry.species,
})))

const selectedBulkPackage = computed(() =>
  bulkManifest.value?.species?.find(entry => entry.species === selectedBulkSpecies.value) || null
)

const loadBulkManifest = async () => {
  bulkLoading.value = true
  bulkError.value = ''
  try {
    const latestResponse = await fetch('/releases/latest.json', { cache: 'no-store' })
    if (!latestResponse.ok) throw new Error(`Release pointer returned ${latestResponse.status}`)
    const latest = await latestResponse.json()
    if (!latest.manifest_url) throw new Error('Release pointer does not contain a manifest URL')

    const manifestResponse = await fetch(latest.manifest_url, { cache: 'no-store' })
    if (!manifestResponse.ok) throw new Error(`Release manifest returned ${manifestResponse.status}`)
    bulkManifest.value = await manifestResponse.json()
    bulkManifestUrl.value = latest.manifest_url

    const species = bulkManifest.value?.species || []
    if (!species.some(entry => entry.species === selectedBulkSpecies.value)) {
      selectedBulkSpecies.value = species[0]?.species || ''
    }
  } catch (error) {
    console.error('Failed to load bulk release manifest:', error)
    bulkError.value = 'Bulk release packages are temporarily unavailable.'
  } finally {
    bulkLoading.value = false
  }
}

const datasets = computed(() => [
  {
    id: 'apa-sites',
    title: 'PA Sites',
    description: 'Sample-resolved PAS positions and relative usage for each transcript',
    icon: 'mdi-map-marker-multiple',
    gradient: 'linear-gradient(135deg, #0D7377, #14919B)',
    countLabel: detailedStats.value.total_apa_sites
      ? `${formatCompactCount(detailedStats.value.total_apa_sites)} PAS clusters`
      : 'PAS clusters',
    countDefinition: COUNT_TERMS.pasClusters,
    formats: ['csv', 'tsv'],
  },
  {
    id: 'bed',
    title: 'Genome Browser Track',
    description: 'PA sites in BED6 format — ready to load into IGV, UCSC Genome Browser, or JBrowse for visualization',
    icon: 'mdi-dna',
    gradient: 'linear-gradient(135deg, #2E7D32, #388E3C)',
    countLabel: 'BED6 format',
    formats: ['bed'],
  },
  {
    id: 'abundance-matrix',
    title: 'Sample Abundance Matrix',
    description: 'Supporting read counts and relative usage for each transcript-PAS association across sample groups',
    icon: 'mdi-table-large',
    gradient: 'linear-gradient(135deg, #355C7D, #4A7898)',
    countLabel: 'Transcript-PAS × Samples',
    countDefinition: COUNT_TERMS.abundanceMatrix,
    formats: ['tsv', 'csv'],
  },
])

const selectDataset = (item) => {
  selectedDataset.value = item
  selectedFormat.value = item.formats[0]
  if (!sampleFilterEnabled.value) selectedSamples.value = []
}

const triggerDownload = async () => {
  if (!downloadUrl.value) return
  downloading.value = true
  try {
    const response = await fetch(downloadUrl.value)
    if (!response.ok) throw new Error(`Server returned ${response.status}`)
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = downloadFilename.value
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(objectUrl)
  } catch (err) {
    console.error('Download failed:', err)
  } finally {
    downloading.value = false
  }
}

const BASE_URL = '/api/v1'

const apiOrigin = computed(() => {
  if (typeof window === 'undefined' || !window.location?.origin) return ''
  return window.location.origin
})

const apiDownloadBaseUrl = computed(() => `${apiOrigin.value}${BASE_URL}/download`)

const downloadUrl = computed(() => {
  if (!selectedDataset.value) return ''
  const params = new URLSearchParams()
  if (selectedSpecies.value) params.set('species', selectedSpecies.value)
  if (sampleFilterEnabled.value) {
    selectedSamples.value.forEach(sample => params.append('sample', sample))
  }
  if (selectedDataset.value.formats.length > 1) params.set('format', selectedFormat.value)
  const query = params.toString()
  return `${BASE_URL}/download/${selectedDataset.value.id}${query ? '?' + query : ''}`
})

const downloadFilename = computed(() => {
  if (!selectedDataset.value) return ''
  const sp = selectedSpecies.value ? `_${selectedSpecies.value.toLowerCase().replace(/\s+/g, '_')}` : ''
  const sampleSuffix = selectedSamples.value.length ? `_samples-${selectedSamples.value.length}` : ''
  return `isoapa_${selectedDataset.value.id}${sp}${sampleSuffix}.${selectedFormat.value}`
})

const buildQueryString = () => {
  const parts = []
  if (selectedDataset.value?.formats.length > 1) parts.push(`format=${selectedFormat.value}`)
  if (selectedSpecies.value) parts.push(`species=${encodeURIComponent(selectedSpecies.value)}`)
  if (sampleFilterEnabled.value) {
    selectedSamples.value.forEach(sample => parts.push(`sample=${encodeURIComponent(sample)}`))
  }
  return parts.length ? '?' + parts.join('&') : ''
}

const curlCommand = computed(() => {
  const dataset = selectedDataset.value?.id || 'apa-sites'
  const qs = buildQueryString()
  const filename = downloadFilename.value || `isoapa_${dataset}.${selectedFormat.value}`
  return `curl -fL -o "${filename}" \\\n  "${apiDownloadBaseUrl.value}/${dataset}${qs}"`
})

const pythonCommand = computed(() => {
  const dataset = selectedDataset.value?.id || 'apa-sites'
  const filename = downloadFilename.value || `isoapa_${dataset}.${selectedFormat.value}`
  const paramItems = []
  if (selectedDataset.value?.formats.length > 1) paramItems.push(`("format", "${selectedFormat.value}")`)
  if (selectedSpecies.value) paramItems.push(`("species", "${selectedSpecies.value}")`)
  if (sampleFilterEnabled.value) {
    selectedSamples.value.forEach(sample => paramItems.push(`("sample", "${sample}")`))
  }
  const paramBlock = paramItems.length ? `\nparams = [\n    ${paramItems.join(',\n    ')}\n]\n` : '\nparams = []\n'
  return `import requests\n\nurl = "${apiDownloadBaseUrl.value}/${dataset}"${paramBlock}\nr = requests.get(url, params=params, timeout=120)\nr.raise_for_status()\nwith open("${filename}", "wb") as f:\n    f.write(r.content)`
})

const rCommand = computed(() => {
  const dataset = selectedDataset.value?.id || 'apa-sites'
  const filename = downloadFilename.value || `isoapa_${dataset}.${selectedFormat.value}`
  const paramLines = []
  if (selectedDataset.value?.formats.length > 1) paramLines.push(`    format = "${selectedFormat.value}",`)
  if (selectedSpecies.value) paramLines.push(`    species = "${selectedSpecies.value}",`)
  if (sampleFilterEnabled.value && selectedSamples.value.length) {
    paramLines.push(`    sample = c(${selectedSamples.value.map(sample => `"${sample}"`).join(', ')}),`)
  }
  const paramBlock = paramLines.length ? `\nparams <- list(\n${paramLines.join('\n')}\n)\n` : '\nparams <- list()\n'
  return `library(httr)\n\nurl <- "${apiDownloadBaseUrl.value}/${dataset}"${paramBlock}\nresponse <- GET(url, query = params, timeout(120))\nstop_for_status(response)\nwriteBin(content(response, "raw"), "${filename}")`
})

const currentCommand = computed(() => {
  if (apiLang.value === 'curl') return curlCommand.value
  if (apiLang.value === 'python') return pythonCommand.value
  return rCommand.value
})

const selectedSpeciesLabel = computed(() => {
  const selected = speciesList.value.find(sp => sp.name === selectedSpecies.value)
  return selected ? formatSpeciesName(selected) : formatSpeciesName(selectedSpecies.value)
})

const sampleFilterEnabled = computed(() =>
  ['apa-sites', 'abundance-matrix'].includes(selectedDataset.value?.id)
)

const sampleSelectionLabel = computed(() => {
  if (selectedSamples.value.length === 1) {
    return formatSampleName(selectedSamples.value[0])
  }
  return `${selectedSamples.value.length} samples`
})

const normalizedSampleKey = (sample) =>
  formatSampleName(sample.display_name ?? sample.name ?? sample)
    .trim()
    .toLowerCase()

const sampleOptions = computed(() => {
  const seen = new Set()
  return sampleList.value
    .filter(sample => !selectedSpecies.value || sample.species === selectedSpecies.value)
    .filter(sample => {
      const key = normalizedSampleKey(sample)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    .map(sample => ({
      title: formatSampleName(sample.display_name ?? sample.name),
      value: sample.name,
      species: sample.species,
    }))
    .sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' }))
})

const filteredSampleOptions = computed(() => {
  return sampleOptions.value
})

const langLabel = (lang) => ({ curl: 'cURL', python: 'Python', r: 'R' }[lang])

const copyCommand = async () => {
  try {
    await navigator.clipboard.writeText(currentCommand.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}

const schemas = [
  { id: 'apa-sites', title: 'PA Sites', fields: [
    { name: 'gene_name', type: 'string', desc: 'Official gene symbol' },
    { name: 'gene_id', type: 'string', desc: 'Gene identifier from the species reference annotation' },
    { name: 'transcript_id', type: 'string', desc: 'Transcript identifier from the species reference annotation' },
    { name: 'site_id', type: 'string', desc: 'Unified PAS cluster identifier; may be shared across transcripts and sample groups' },
    { name: 'cluster_range', type: 'string', desc: 'Genomic span of the PA site, formatted as start:end' },
    { name: 'representative_position', type: 'integer', desc: 'Representative genomic coordinate of the unified PAS cluster' },
    { name: 'sample_site_position', type: 'integer', desc: 'Genomic coordinate of the PA cleavage site as detected in this specific sample' },
    { name: 'site_abundance', type: 'float', desc: 'Relative abundance of this PA site within the transcript for this sample (0–1)' },
    { name: 'species', type: 'string', desc: 'Species name' },
    { name: 'sample', type: 'string', desc: 'Harmonised sample-group name' },
  ]},
  { id: 'bed', title: 'Genome Browser BED', fields: [
    { name: 'chrom', type: 'string', desc: 'Chromosome ID' },
    { name: 'chromStart', type: 'integer', desc: '0-based start position of the PA site' },
    { name: 'chromEnd', type: 'integer', desc: '1-based end position (half-open interval)' },
    { name: 'name', type: 'string', desc: 'Unique PA site identifier' },
    { name: 'score', type: 'string', desc: '.' },
    { name: 'strand', type: 'string', desc: '+ or –' },
  ]},
  { id: 'abundance-matrix', title: 'Abundance Matrix', fields: [
    { name: 'site_id', type: 'string', desc: 'PA site identifier' },
    { name: 'transcript_id', type: 'string', desc: 'Transcript identifier from the species reference annotation' },
    { name: 'gene_name', type: 'string', desc: 'Official gene symbol' },
    { name: 'chromosome', type: 'string', desc: 'Chromosome ID' },
    { name: 'strand', type: 'string', desc: '+ or –' },
    { name: 'species', type: 'string', desc: 'Species name' },
    { name: '[sample_name]_count', type: 'integer', desc: 'Supporting reads for this transcript-PAS association in the sample group' },
    { name: '[sample_name]_relative_abundance', type: 'float', desc: 'PAS usage within the transcript in this sample group (0–1)' },
  ]},
]

const currentSchema = computed(() => schemas.find(s => s.id === schemaTab.value)?.fields || [])

onMounted(async () => {
  loadBulkManifest()
  try {
    const [stats, species, samples] = await Promise.all([
      apiService.getDetailedStats(),
      apiService.getSpecies(),
      apiService.getSamples()
    ])
    detailedStats.value = stats || {}
    // Depending on API response, it might be an array of strings or objects. Handling both:
    if (species && species.length > 0) {
      if (typeof species[0] === 'string') {
        speciesList.value = species.map(s => ({ id: s, name: s }))
      } else {
        speciesList.value = species
      }
    }
    sampleList.value = (samples || []).sort((a, b) =>
      (a.display_name ?? formatSampleName(a.name)).localeCompare(
        b.display_name ?? formatSampleName(b.name),
        undefined,
        { sensitivity: 'base' }
      )
    )
  } catch (err) {
    console.error('Failed to load download filters:', err)
  }
})

watch(selectedSpecies, () => {
  const available = new Set(filteredSampleOptions.value.map(sample => sample.value))
  const seen = new Set()
  selectedSamples.value = selectedSamples.value.filter(sample => {
    const key = formatSampleName(sample).toLowerCase()
    if (!available.has(sample) || seen.has(key)) return false
    seen.add(key)
    return true
  })
})

watch(sampleFilterEnabled, (enabled) => {
  if (!enabled) selectedSamples.value = []
})
</script>

<style scoped>
.download-page {
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

.dataset-cards-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}
@media (max-width: 767px) {
  .dataset-cards-row { grid-template-columns: 1fr; }
}
.dataset-card {
  background: #fff;
  border: 1px solid #dbe3ea;
  border-radius: 24px;
  padding: 28px 24px;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
  box-shadow: none;
  position: relative;
  overflow: hidden;
}
.dataset-card:hover {
  border-color: #b9cbd2;
  background: #fff;
}
.dataset-card--selected {
  border: 1px solid #14919B !important;
  box-shadow: none !important;
  background: #f8fcfc !important;
}
.dataset-card-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: none;
}
.dataset-card-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
}
.dataset-card-desc {
  font-size: 0.82rem;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 16px;
}
.dataset-card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.scope-panel {
  background: #fff !important;
  border: 1px solid #dbe3ea !important;
  border-radius: 24px;
  box-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  padding: 20px 28px;
  display: flex;
  align-items: flex-start;
  gap: 32px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}
.scope-group { display: flex; flex-direction: column; gap: 10px; }
.scope-group--samples {
  width: min(880px, 100%);
  flex: 0 0 min(880px, 100%);
  align-items: center;
}

.scope-group--samples .scope-label {
  width: min(880px, 100%);
  justify-content: flex-start;
}
.scope-group--format {
  flex: 0 0 auto;
}
.scope-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #94a3b8;
  display: flex;
  align-items: center;
}
.scope-label-hint {
  margin-left: 8px;
  color: #14919B;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: none;
}
.scope-chips-row { display: flex; flex-wrap: wrap; gap: 8px; }
.scope-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 16px;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease, background 0.2s ease;
  gap: 4px;
}
.scope-chip:hover {
  border-color: #14919B;
  color: #0D7377;
}
.scope-chip.active {
  background: linear-gradient(135deg, #0D7377, #14919B);
  border-color: #14919B;
  color: white;
  box-shadow: none;
}
.scope-chip-latin {
  font-style: italic;
  font-size: 0.75rem;
  opacity: 0.75;
  margin-left: 2px;
}
.scope-chip.active .scope-chip-latin { opacity: 0.85; }
.scope-divider {
  width: 1px;
  background: #e2e8f0;
  align-self: stretch;
  min-height: 40px;
}
.scope-divider--format {
  margin-left: 0;
  margin-right: -14px;
}
@media (max-width: 600px) { .scope-divider { display: none; } }

.sample-multi-select {
  width: min(880px, 100%);
  min-width: 280px;
}

.sample-multi-select :deep(.v-field) {
  min-height: 44px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #dbe3ea;
  box-shadow: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.sample-multi-select :deep(.v-field:hover) {
  border-color: #14919B;
  background: rgba(13, 115, 119, 0.035);
  box-shadow: none;
}

.sample-multi-select :deep(.v-field--focused) {
  background: #fff;
  border-color: #0D7377;
  box-shadow: 0 0 0 4px rgba(20, 145, 155, 0.10);
}

.sample-multi-select :deep(.v-field__input) {
  min-height: 44px;
  padding: 5px 10px 5px 16px;
  gap: 6px;
}

.sample-multi-select :deep(.v-field__outline) {
  color: transparent;
}

.sample-multi-select :deep(.v-field__append-inner) {
  color: #0D7377;
  padding-inline-start: 8px;
  padding-inline-end: 12px;
}

.sample-select-chip {
  min-height: 26px !important;
  border-radius: 999px !important;
  background: rgba(13, 115, 119, 0.08) !important;
  border: 1px solid rgba(13, 115, 119, 0.16) !important;
  color: #0D7377 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

.sample-multi-select :deep(.v-field__input input::placeholder) {
  color: #475569;
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0;
  opacity: 0.92;
}

.sample-option-subtitle {
  color: #94a3b8;
  font-size: 0.76rem;
}

:global(.sample-select-menu .v-overlay__content) {
  border-radius: 22px !important;
  border: 1px solid #dbe3ea !important;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.10) !important;
  overflow: hidden !important;
}

:global(.sample-select-menu .v-list) {
  padding: 10px !important;
  background: #ffffff !important;
}

:global(.sample-select-menu .v-list-item) {
  border-radius: 999px !important;
  min-height: 38px !important;
  margin-bottom: 4px !important;
  padding-inline: 14px !important;
}

:global(.sample-select-menu .v-list-item-title) {
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  line-height: 1.25 !important;
  letter-spacing: 0 !important;
  color: #475569 !important;
}

:global(.sample-select-menu .v-list-item:hover) {
  background: rgba(13, 115, 119, 0.07) !important;
}

:global(.sample-select-menu .v-list-item--active) {
  background: rgba(13, 115, 119, 0.10) !important;
  color: #0D7377 !important;
}

:global(.sample-select-menu .v-list-item--active .v-list-item-title) {
  color: #0D7377 !important;
  font-weight: 600 !important;
}

.download-action-panel {
  background: #f0fdfa;
  border: 1px solid #b7dad7;
  border-radius: 24px;
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 32px;
  box-shadow: none;
  flex-wrap: wrap;
}
.download-action-eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #14919B;
  margin-bottom: 6px;
}
.download-action-title {
  font-size: 1.4rem;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 10px;
}
.download-action-species {
  color: #14919B;
}
.download-btn {
  background: linear-gradient(135deg, #0D7377, #14919B) !important;
  color: white !important;
  font-weight: 700 !important;
  letter-spacing: 0.05em !important;
  border-radius: 14px !important;
  padding: 0 32px !important;
  box-shadow: none !important;
  transition: background 0.2s ease !important;
  flex-shrink: 0;
}
.download-btn:hover {
  background: #0b686c !important;
}

.bulk-section {
  scroll-margin-top: 88px;
  margin-bottom: 32px;
}

.bulk-card {
  padding: 24px 28px 26px;
  background: #fff;
  border: 1px solid #dbe3ea;
  border-radius: 24px;
  box-shadow: none;
}

.bulk-card-header,
.bulk-title-row,
.bulk-package,
.bulk-package-main,
.bulk-package-actions,
.bulk-contents,
.api-card-header,
.api-reference-link,
.manifest-link,
.bulk-download-btn,
.bulk-state {
  display: flex;
  align-items: center;
}

.bulk-card-header,
.bulk-package,
.api-card-header {
  justify-content: space-between;
}

.bulk-card-header {
  gap: 20px;
  margin-bottom: 20px;
}

.bulk-title-row {
  gap: 10px;
}

.bulk-card-title {
  margin: 0;
  color: #1e293b;
  font-size: 1.2rem;
  font-weight: 700;
}

.bulk-card-subtitle {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 0.85rem;
}

.release-badge {
  padding: 3px 8px;
  color: #0d7377;
  background: #effafa;
  border: 1px solid #c9e7e5;
  border-radius: 7px;
  font-size: 0.72rem;
  font-weight: 700;
}

.manifest-link,
.api-reference-link {
  gap: 6px;
  flex: 0 0 auto;
  color: #0d7377;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
}

.manifest-link:hover,
.api-reference-link:hover {
  color: #0a5c5f;
}

.bulk-state {
  gap: 10px;
  min-height: 82px;
  justify-content: center;
  color: #64748b;
}

.bulk-state--error {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 12px;
}

.bulk-species-select {
  max-width: 460px;
  margin-bottom: 18px;
}

.bulk-species-select :deep(.v-field) {
  min-height: 44px;
  background: #fff;
  border: 1px solid #dbe3ea;
  border-radius: 12px;
}

.bulk-species-select :deep(.v-field__outline) {
  color: transparent;
}

.bulk-package {
  gap: 18px;
  padding: 18px 20px;
  background: #f8fbfb;
  border: 1px solid #d8e9e7;
  border-radius: 16px;
}

.bulk-package-main {
  min-width: 0;
  gap: 13px;
}

.bulk-package-icon {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  place-items: center;
  color: #0d7377;
  background: #dff5f4;
  border-radius: 12px;
}

.bulk-package-name {
  color: #1e293b;
  font-family: var(--aa-font-mono);
  font-size: 0.86rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.bulk-package-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 6px;
  color: #64748b;
  font-size: 0.78rem;
  flex-wrap: wrap;
}

.bulk-count { display: inline-flex; align-items: center; }
.bulk-meta-separator {
  width: 3px;
  height: 3px;
  flex-shrink: 0;
  background: #94a3b8;
  border-radius: 50%;
}

.bulk-package-actions {
  flex: 0 0 auto;
  gap: 14px;
}

.bulk-download-btn {
  gap: 7px;
  padding: 10px 16px;
  color: #fff;
  background: #0d7377;
  border-radius: 10px;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
}

.bulk-download-btn:hover {
  background: #0a5c5f;
}

.bulk-contents {
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-top: 16px;
  color: #64748b;
  font-size: 0.78rem;
}

.bulk-contents span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.api-card {
  background: #fff !important;
  border: 1px solid #dbe3ea !important;
  border-radius: 24px;
  padding: 22px 32px 32px;
  box-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  margin-bottom: 32px;
}
.api-card-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}
.api-card-subtitle {
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 0;
}
.api-card-header {
  gap: 20px;
  margin-bottom: 24px;
}
.lang-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 0;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0;
}
.lang-tab {
  padding: 10px 20px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #94a3b8;
  background: none;
  border: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.2s, border-color 0.2s;
}
.lang-tab:hover { color: #0D7377; }
.lang-tab.active {
  color: #0D7377;
  border-bottom-color: #14919B;
}
.code-block {
  position: relative;
  background: #0f172a;
  border-radius: 0 0 12px 12px;
  padding: 24px;
  border: 1px solid #1e293b;
  border-top: none;
}
.code-text {
  color: #e2e8f0;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
.copy-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.copy-btn:hover {
  background: rgba(20,145,155,0.25);
  color: #14919B;
  border-color: #14919B;
}

.schema-section {
  background: #fff;
  border: 1px solid #dbe3ea;
  border-radius: 24px;
  padding: 24px 32px;
  box-shadow: none;
}
.schema-panel {
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
.schema-panel.is-open {
  max-height: 620px;
  opacity: 1;
  transform: translateY(0);
}
.schema-panel > * {
  transform: translateY(-4px);
  transition: transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
}
.schema-panel.is-open > * {
  transform: translateY(0);
}
.schema-toggle-btn {
  display: flex;
  align-items: center;
  background: none;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  color: #0D7377;
  cursor: pointer;
  padding: 0;
}
.schema-toggle-btn:hover { text-decoration: underline; }
.schema-table-wrapper {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  margin-top: 0;
}
.schema-tabs {
  border-bottom: 0;
  margin-bottom: 10px;
  padding-left: 12px;
}
.field-badge {
  background: #f0fdfa;
  color: #0D7377;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.82rem;
  border: 1px solid rgba(13,115,119,0.2);
  font-family: var(--aa-font-mono);
}
.type-badge {
  font-size: 0.78rem;
  font-weight: 600;
  color: #355C7D;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 4px;
}
.elegant-table { background: transparent !important; }
.elegant-table :deep(.v-table__wrapper),
.elegant-table :deep(table),
.elegant-table :deep(thead),
.elegant-table :deep(tr:first-child th) {
  border-top: 0 !important;
}
.elegant-table :deep(th) {
  background: #f8fafc !important;
  font-size: 0.8rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: #64748b !important;
  box-shadow: none !important;
}
.elegant-table :deep(td) {
  border-bottom: 1px solid #f1f5f9 !important;
  font-family: var(--aa-font-sans) !important;
}
.elegant-table :deep(tr:hover td) { background: #f0fdfa !important; }

@media (max-width: 900px) {
  .scope-panel {
    gap: 20px;
  }

  .scope-divider {
    display: none;
  }

  .scope-group,
  .scope-group--samples,
  .scope-group--format,
  .scope-group--samples .scope-label,
  .sample-multi-select {
    align-items: stretch;
    flex: 1 1 100%;
    width: 100%;
  }
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

  .dataset-cards-row {
    gap: 14px;
  }

  .dataset-card {
    border-radius: 18px;
    padding: 22px 18px;
  }

  .scope-panel,
  .bulk-card,
  .api-card,
  .download-action-panel {
    padding: 18px;
    border-radius: 18px;
  }

  .scope-chip {
    justify-content: center;
    min-height: 34px;
  }

  .scope-chip-latin {
    display: block;
    margin-left: 0;
  }

  .download-action-panel {
    align-items: stretch;
  }

  .download-action-title {
    font-size: 1.12rem;
    line-height: 1.35;
  }

  .download-btn {
    width: 100%;
  }

  .bulk-card-header,
  .bulk-package,
  .api-card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .bulk-species-select {
    max-width: none;
  }

  .bulk-package-actions {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
  }

  .bulk-download-btn {
    justify-content: center;
    width: 100%;
  }

  .lang-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .lang-tab {
    flex: 0 0 auto;
    padding: 9px 16px;
  }

  .code-block {
    padding: 18px 14px 58px;
    overflow-x: auto;
  }

  .code-text {
    white-space: pre;
    word-break: normal;
    min-width: 560px;
  }

  .copy-btn {
    bottom: 12px;
    left: 14px;
    right: auto;
    top: auto;
  }

  .schema-table-wrapper {
    overflow-x: auto;
  }

  .schema-table-wrapper :deep(table) {
    min-width: 720px;
  }
}
</style>
