<template>
  <section class="section-card architecture-card" :class="{ 'architecture-card--transcript': viewMode === 'transcript' }">
    <div class="architecture-head">
      <div>
        <div class="section-eyebrow">Comparative Usage</div>
        <h2>PAS positions and usage</h2>
        <p>Each gene is anchored at its distal PAS. Larger marks indicate greater relative usage.</p>
      </div>
    </div>
    <div class="architecture-controls">
      <div class="control-group">
        <span class="control-label">Resolution</span>
        <div class="view-toggle" role="group" aria-label="Comparison granularity">
          <button
            v-for="mode in VIEW_MODES"
            :key="mode.value"
            class="view-toggle-btn"
            :class="{ 'is-active': viewMode === mode.value }"
            type="button"
            :aria-pressed="viewMode === mode.value"
            @click="$emit('update:viewMode', mode.value)"
          >
            {{ mode.title }}
          </button>
        </div>
      </div>
      <div class="control-group sample-control">
        <span class="control-label">Sample group</span>
        <v-autocomplete
          :model-value="sampleKey"
          :items="sampleOptions"
          item-title="title"
          item-value="value"
          aria-label="Sample group for PAS usage"
          variant="outlined"
          density="compact"
          hide-details
          class="sample-select"
          @update:model-value="$emit('update:sampleKey', $event)"
        ></v-autocomplete>
      </div>
      <div class="control-group scale-control">
        <span class="control-label">Distance scale</span>
        <div class="view-toggle" role="group" aria-label="Distance scale">
          <button
            v-for="option in SCALE_OPTIONS"
            :key="option.value"
            class="view-toggle-btn"
            :class="{ 'is-active': scale === option.value }"
            type="button"
            :aria-pressed="scale === option.value"
            :title="option.hint"
            @click="$emit('update:scale', option.value)"
          >
            {{ option.title }}
          </button>
        </div>
      </div>
    </div>

    <p class="usage-caption">
      {{ viewMode === 'gene' ? 'Usage pools reads across all transcripts in each sample group.' : 'Usage is calculated within each individual transcript.' }}
      <span v-if="!sampleKey"> Showing the mean across groups supporting each PAS.</span>
    </p>

    <div class="architecture-legend">
      <span class="legend-label">PAS evidence</span>
      <span v-for="entry in visibleLegend" :key="entry.key" class="legend-item">
        <i class="legend-dot" :class="`legend-dot--${entry.key}`"></i>{{ entry.label }}
      </span>
      <span class="legend-item">
        <i class="legend-dot legend-dot--muted"></i>
        Not called
      </span>
      <span class="legend-item legend-item--scale">
        <i class="legend-dot legend-dot--small"></i>
        <i class="legend-dot legend-dot--large"></i>
        Lower to higher usage
      </span>
    </div>

    <!--
      This grid must stay identical to .pas-row in PasTrack.vue at every
      breakpoint, or the ticks stop marking the distances the marks are drawn at.
    -->
    <div class="pas-axis">
      <span class="pas-axis-title">bp upstream of distal PAS</span>
      <div ref="axisElement" class="pas-axis-scale">
        <span
          v-for="tick in ticks"
          :key="tick.distance"
          class="pas-axis-tick"
          :class="tickAlignment(tick)"
          :style="{ left: `${tick.fraction * 100}%` }"
        >
          <i></i><em>{{ tick.label }}</em>
        </span>
      </div>
      <span class="pas-axis-meta">{{ viewMode === 'gene' ? 'PAS span' : 'PA sites' }}</span>
    </div>

    <div class="pas-rows">
      <template v-for="(gene, geneIndex) in resolvedGenes" :key="`${geneIndex}:${gene.gene_db_id}`">
        <div v-if="viewMode === 'gene'" class="pas-gene-block">
          <PasTrack
            :label="gene.gene_name"
            :sublabel="gene.scientific_name"
            :meta="gene.reachLabel"
            :meta-title="gene.reachTitle"
            :to="gene.detailRoute"
            :points="gene.genePoints"
            usage-label="Gene usage"
            :sample-key="sampleKey"
            empty-message="No transcript-linked PA sites available."
          />
        </div>
        <div v-else class="pas-species-group">
          <div class="pas-species-head">
            <div class="pas-species-identity">
              <router-link :to="gene.detailRoute" class="pas-species-gene">{{ gene.gene_name }}</router-link>
              <span class="pas-species-name">{{ gene.scientific_name }}</span>
            </div>
            <span class="pas-species-locus" :title="gene.anchorTitle">
              {{ gene.chromosome }} · {{ gene.strand }} · {{ gene.anchorLabel }}
            </span>
          </div>
          <div v-if="gene.transcriptTracks.length" class="pas-transcript-list">
            <PasTrack
              v-for="(transcript, transcriptIndex) in gene.transcriptTracks"
              :key="`${transcriptIndex}:${transcript.transcript_id}`"
              dense
              :label="transcript.transcript_id"
              :sublabel="transcript.biotypeLabel"
              :meta="`${transcript.points.length} PAS`"
              :to="transcript.locusRoute"
              :points="transcript.points"
              usage-label="Transcript usage"
              :sample-key="sampleKey"
            />
          </div>
          <div v-if="!gene.transcriptTracks.length" class="pas-species-empty">
            No transcript-linked PA sites available.
          </div>
          <div v-else-if="gene.hiddenTranscripts > 0" class="pas-species-note">
            Showing {{ gene.transcriptTracks.length }} of {{ gene.transcript_count }} transcripts.
            Gene-level usage includes all {{ gene.transcript_count }} transcripts.
            <router-link :to="gene.detailRoute">View complete locus</router-link>.
          </div>
        </div>
      </template>
    </div>

    <details class="architecture-notes">
      <summary>How to read this comparison</summary>
      <div class="architecture-note-content">
        <p><strong>Gene level:</strong> reads supporting a PAS are summed across every transcript, then divided by all PAS-supporting reads for that gene in the same sample group.</p>
        <p><strong>Transcript level:</strong> each PAS retains its within-transcript relative usage. Mean usage averages the fractions from groups supporting that site; an absent call is not treated as measured zero.</p>
        <p><strong>Position:</strong> distances share one scale, with each gene anchored independently at its distal observed PAS. Site numbers are local to each gene and remain consistent between views. These positions do not establish PAS conservation.</p>
        <p><strong>Coverage:</strong> sampling and reference annotations differ across species. Matching sample names identifies similar labels, not matched experiments.</p>
      </div>
    </details>
  </section>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import PasTrack from './PasTrack.vue'
import {
  AXIS_SCALE_LINEAR,
  AXIS_SCALE_LOG,
  PAS_LEVEL_LEGEND,
  axisMaxUpstream,
  axisTicks,
  buildTrackPoints,
  distalAnchor,
  formatBiotype,
  formatUpstreamExtent,
  geneLevelSites,
  geneUpstreamExtent
} from '@/utils/pasLayout'

const props = defineProps({
  genes: { type: Array, default: () => [] },
  sampleOptions: { type: Array, default: () => [] },
  sampleKey: { type: String, default: '' },
  viewMode: { type: String, default: 'gene' },
  scale: { type: String, default: AXIS_SCALE_LINEAR }
})

defineEmits(['update:sampleKey', 'update:viewMode', 'update:scale'])

const VIEW_MODES = [
  { value: 'gene', title: 'Gene level' },
  { value: 'transcript', title: 'Transcript level' }
]

const SCALE_OPTIONS = [
  {
    value: AXIS_SCALE_LINEAR,
    title: 'Linear bp',
    hint: 'Equal base pairs take equal width.'
  },
  {
    value: AXIS_SCALE_LOG,
    title: 'Log bp',
    hint: 'Expands the region near the distal site, so one far-upstream site cannot flatten every other row against the right edge.'
  }
]

/*
 * One extent shared by every row. A per-row scale would make horizontal position
 * incomparable across species, which is the whole point of the view.
 */
const maxUpstream = computed(() => axisMaxUpstream(props.genes))

const axisElement = ref(null)
const axisWidth = ref(900)
let axisObserver
onMounted(() => {
  axisObserver = new ResizeObserver(([entry]) => { axisWidth.value = entry.contentRect.width })
  if (axisElement.value) axisObserver.observe(axisElement.value)
})
onBeforeUnmount(() => axisObserver?.disconnect())
const ticks = computed(() => axisTicks(maxUpstream.value, props.scale, axisWidth.value))
const visibleLegend = computed(() => PAS_LEVEL_LEGEND.filter(entry =>
  entry.key !== 'unassigned' || props.genes.some(gene => geneLevelSites(gene).some(site => !['PAS-L1', 'PAS-L2', 'PAS-L3'].includes(site.pa_level)))
))

/*
 * The rule is what must sit exactly on the tick's fraction, so the label shifts
 * around it. The end labels pull fully inside the box rather than overflowing it.
 */
const tickAlignment = tick => {
  if (tick.fraction <= 0.001) return 'pas-axis-tick--start'
  if (tick.fraction >= 0.999) return 'pas-axis-tick--end'
  return 'pas-axis-tick--mid'
}

const resolvedGenes = computed(() =>
  props.genes.map(gene => {
    const anchor = distalAnchor(gene)
    const context = {
      strand: gene.strand,
      anchor,
      maxUpstream: maxUpstream.value,
      scale: props.scale,
      sampleKey: props.sampleKey
    }
    const transcripts = gene.transcripts || []
    const hiddenTranscripts = Math.max(0, (gene.transcript_count || 0) - transcripts.length)
    const reach = formatUpstreamExtent(geneUpstreamExtent(gene))
    const scope = `All ${gene.transcript_count} observed transcripts contribute to this gene profile.`
    return {
      ...gene,
      reachLabel: geneLevelSites(gene).length ? reach : 'No sites',
      reachTitle: scope,
      anchorLabel: anchor.empty ? 'no anchor' : `distal ${anchor.position.toLocaleString()}`,
      anchorTitle: anchor.empty
        ? 'No positioned PA sites for this gene, so no distance can be measured.'
        : `${scope} Distal PAS: ${anchor.position.toLocaleString()} on ${gene.chromosome}.`,
      detailRoute: {
        name: 'GeneDetail',
        params: { geneId: gene.gene_db_id },
        query: { species: gene.species }
      },
      genePoints: buildTrackPoints(geneLevelSites(gene), context),
      shownTranscripts: transcripts.length,
      hiddenTranscripts,
      // Transcript tracks are only rendered in transcript view; laying them out
      // in gene view would build points that are immediately discarded.
      transcriptTracks:
        props.viewMode === 'transcript'
          ? transcripts.map(transcript => ({
              transcript_id: transcript.transcript_id,
              biotypeLabel: formatBiotype(transcript.transcript_biotype),
              locusRoute: {
                name: 'LocusDetail',
                params: { transcriptId: transcript.transcript_id },
                query: { species: gene.species }
              },
              points: buildTrackPoints(transcript.sites || [], context)
            }))
          : []
    }
  })
)

</script>

<style scoped>
.architecture-card {
  --pas-group-inset: 18px;
  --pas-axis-inset: 0px;
  --pas-gutter: 190px;
  --pas-meta: 114px;
  --pas-track-height: 58px;
  --pas-track-height-dense: 48px;
  --pas-l1: #0d7377;
  --pas-l2: #d3a05c;
  --pas-l3: #8c89b0;
  padding: 24px;
  overflow: visible;
}
.architecture-card--transcript {
  /* Match the transcript group's border and content padding exactly. */
  --pas-axis-inset: calc(var(--pas-group-inset) + 1px);
}

.architecture-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.architecture-head h2 {
  margin: 10px 0 7px;
  color: var(--aa-slate-800);
  font-size: var(--compare-title-size, 1.38rem);
  font-weight: 600;
  line-height: 1.3;
}
.architecture-head p {
  margin: 0;
  color: var(--aa-slate-500);
  font-size: var(--compare-body-size, 0.92rem);
  line-height: 1.55;
}
.architecture-controls {
  display: grid;
  grid-template-columns: auto minmax(260px, 1fr) auto;
  align-items: end;
  gap: 24px;
  margin-top: 22px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
}
.control-group { min-width: 0; }
.control-label { display: block; margin-bottom: 7px; color: #475569; font-size: 0.82rem; font-weight: 500; }
.usage-caption { margin: 12px 0 0; font-size: 0.85rem; color: #64748b; line-height: 1.6; }

.view-toggle {
  display: inline-flex;
  padding: 3px;
  border: 1px solid rgba(203, 213, 225, 0.8);
  border-radius: 10px;
  background: var(--aa-slate-050);
}
.view-toggle-btn {
  padding: 7px 14px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--aa-slate-600);
  min-height: 34px;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
}
.view-toggle-btn.is-active {
  background: #ffffff;
  color: var(--aa-teal-800);
  box-shadow: none;
}
.sample-select { width: 100%; }
.sample-select :deep(.v-field) { border-radius: 9px; background: #ffffff; }
.sample-select :deep(.v-field__input) { font-size: 0.9rem; }

.architecture-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 18px;
  margin: 18px 0 6px;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
  color: var(--aa-slate-600);
  font-size: 0.82rem;
}
.legend-label { font-weight: 600; }
.legend-item { display: inline-flex; align-items: center; gap: 7px; }
.legend-item--scale { margin-left: auto; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--aa-slate-300); }
.legend-dot--l1 { background: var(--pas-l1); }
.legend-dot--l2 { background: var(--pas-l2); }
.legend-dot--l3 { background: var(--pas-l3); }
.legend-dot--unassigned { background: var(--aa-slate-100); border: 1.5px dashed var(--aa-slate-300); }
/* Matches .pas-mark--muted: hollow, solid ring in the site's own level colour. */
.legend-dot--muted { background: #ffffff; border: 2px solid var(--aa-slate-500); }
.legend-dot--small { width: 7px; height: 7px; background: var(--aa-teal-700); }
.legend-dot--large { width: 14px; height: 14px; background: var(--aa-teal-700); }

.pas-axis {
  display: grid;
  grid-template-columns: var(--pas-gutter) 1fr var(--pas-meta);
  align-items: end;
  gap: 0 14px;
  padding: 16px var(--pas-axis-inset) 4px;
}
.pas-axis-title,
.pas-axis-meta {
  padding-bottom: 6px;
  color: var(--aa-slate-500);
  font-size: 0.79rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-align: right;
}
.pas-axis-scale {
  position: relative;
  height: 28px;
  border-bottom: 1px solid var(--aa-slate-200);
}
/*
 * Zero-width anchors: the rule line sits exactly on the tick fraction while the
 * label is free to shift, so the end labels stay inside the scale box instead of
 * overflowing it (furthest upstream to the left, 'distal PAS' past the meta column).
 */
.pas-axis-tick { position: absolute; bottom: 0; width: 0; }
.pas-axis-tick i {
  display: block;
  width: 1px;
  height: 6px;
  background: var(--aa-slate-300);
}
.pas-axis-tick em {
  display: block;
  width: max-content;
  color: var(--aa-slate-500);
  font-size: 0.76rem;
  font-style: normal;
  white-space: nowrap;
}
.pas-axis-tick--mid em { transform: translateX(-50%); }
.pas-axis-tick--start em { transform: translateX(0); }
.pas-axis-tick--end i { transform: translateX(-1px); }
.pas-axis-tick--end em { transform: translateX(-100%); }

.pas-rows { display: flex; flex-direction: column; }
.pas-gene-block { border-bottom: 1px solid rgba(226, 232, 240, 0.8); }
.pas-gene-block:last-child { border-bottom: 0; }

.pas-species-group {
  margin-top: 16px;
  border: 1px solid #dce8e8;
  border-radius: 14px;
  background: #ffffff;
}
.pas-species-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px 20px;
  padding: 14px var(--pas-group-inset);
  border-bottom: 1px solid #e1ebeb;
  border-radius: 13px 13px 0 0;
  background: #f2f8f7;
}
.pas-species-identity { display: flex; flex-wrap: wrap; align-items: baseline; gap: 5px 12px; min-width: 0; }
.pas-transcript-list { padding: 4px var(--pas-group-inset) 10px; }
.pas-transcript-list :deep(.pas-row--dense) { padding: 9px 0; }
.pas-transcript-list :deep(.pas-row--dense + .pas-row--dense) { border-top: 1px solid #edf2f3; }
.pas-species-gene {
  color: var(--aa-slate-800);
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
}
.pas-species-gene:hover { color: var(--aa-teal-700); }
.pas-species-name { color: var(--aa-slate-600); font-size: 0.86rem; }
.pas-species-locus {
  margin-left: auto;
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--aa-slate-500);
  font-family: var(--aa-font-sans);
  font-size: 0.79rem;
}
.pas-species-empty,
.pas-species-note {
  padding: 12px var(--pas-group-inset) 16px;
  color: var(--aa-slate-500);
  font-size: 0.82rem;
  line-height: 1.45;
}

.architecture-notes {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--aa-slate-200);
}
.architecture-notes summary { width: fit-content; color: #0d7377; font-size: 0.86rem; font-weight: 500; cursor: pointer; }
.architecture-note-content { margin-top: 12px; max-width: 960px; }
.architecture-notes p {
  margin: 0 0 6px;
  color: var(--aa-slate-500);
  font-size: 0.85rem;
  line-height: 1.6;
}
.architecture-notes p:last-child { margin-bottom: 0; }

@media (max-width: 960px) {
  .architecture-card { --pas-gutter: 160px; --pas-meta: 108px; padding: 20px; }
  .architecture-head { flex-direction: column; }
  .architecture-controls { grid-template-columns: 1fr auto; gap: 14px; }
  .sample-control { grid-column: 1 / -1; grid-row: 2; }
  .sample-select { width: 100%; }
  .legend-item--scale { margin-left: 0; }
}

@media (max-width: 640px) {
  /*
   * PasTrack stacks .pas-row into a single full-width column at this
   * breakpoint, so the axis collapses to the same single column: the scale box
   * then spans exactly the box the marks are positioned in. The shared inset
   * accounts for the transcript group's border and padding. Keeping a
   * gutter/meta column on the axis only would offset the ticks from the marks
   * by the gutter plus one grid gap. The axis title moves above the scale and
   * the meta heading drops, since the rows' meta column has stacked away too.
   */
  .architecture-card { --pas-group-inset: 14px; padding: 18px; }
  .pas-species-head { padding-block: 12px; gap: 5px; }
  .pas-species-identity { width: 100%; }
  .pas-species-locus { margin-left: 0; line-height: 1.5; }
  .architecture-controls { grid-template-columns: 1fr; padding: 12px; }
  .sample-control { grid-row: auto; }
  .view-toggle { width: 100%; }
  .view-toggle-btn { flex: 1; }
  .pas-axis { grid-template-columns: 1fr; gap: 4px; }
  .pas-axis-title { padding-bottom: 0; text-align: left; }
  .pas-axis-meta { display: none; }
}
</style>
