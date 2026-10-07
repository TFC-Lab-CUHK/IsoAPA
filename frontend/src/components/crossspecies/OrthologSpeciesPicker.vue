<template>
  <section class="section-card picker-card">
    <div class="picker-head">
      <div>
        <div class="section-eyebrow">Ortholog Selection</div>
        <h2>Compared genes</h2>
        <p>
          {{ orthologSet.source_gene.gene_name }} · {{ orthologSet.ortholog_count }} orthologs available · {{ selectedIds.length }} of {{ maxSelection }} selected
        </p>
      </div>
      <div class="picker-actions">
        <button v-if="orthologSet.ortholog_count" class="picker-action picker-action--primary" type="button" :aria-expanded="showAll" @click="showAll = !showAll">
          {{ showAll ? 'Done' : 'Choose orthologs' }}
          <v-icon :icon="showAll ? 'mdi-chevron-up' : 'mdi-chevron-down'" size="16" />
        </button>
        <button
          class="picker-action"
          type="button"
          :disabled="selectedIds.length <= 1"
          @click="clearExtras"
        >
          Reset
        </button>
        <router-link :to="sourceDetailRoute" class="picker-link">
          View source gene
          <v-icon icon="mdi-arrow-right" size="15"></v-icon>
        </router-link>
      </div>
    </div>

    <v-alert v-if="!orthologSet.ortholog_count" type="info" variant="tonal" class="mt-5">
      No curated ortholog relationship is available for this gene in the current IsoAPA species set.
    </v-alert>

    <input v-if="showAll" v-model="search" class="picker-search" type="search" placeholder="Filter species or genes" aria-label="Filter ortholog species or genes" />

    <div class="picker-grid" :class="{ 'picker-grid--expanded': showAll }">
      <!--
        Disabled cards use aria-disabled, not the `disabled` attribute: `disabled`
        drops them out of the tab order, so keyboard and screen-reader users could
        never discover that the source species is present-but-fixed, or why a card
        refuses selection. Activation is suppressed in `toggle`/`onKeydown` instead.
      -->
      <button
        v-for="gene in visibleCards"
        :key="gene.gene_db_id"
        class="picker-cardlet"
        :class="{ 'is-selected': gene.selected, 'is-source': gene.isSource }"
        type="button"
        role="checkbox"
        :aria-checked="gene.selected"
        :aria-disabled="gene.disabled ? 'true' : 'false'"
        :title="gene.disabledReason || null"
        @click="toggle(gene)"
        @keydown="onKeydown($event, gene)"
      >
        <span class="picker-check" aria-hidden="true">
          <v-icon v-if="gene.selected" icon="mdi-check" size="13"></v-icon>
        </span>
        <span class="picker-species">{{ gene.scientific_name }}</span>
        <span class="picker-gene">
          {{ gene.gene_name }}
          <em v-if="gene.isSource" class="picker-source-badge">Source</em>
        </span>
        <span v-if="showAll" class="picker-geneid">GeneID {{ gene.gene_id || 'not available' }}</span>
        <span class="picker-stats">
          {{ formatCount(gene.transcript_count) }} {{ gene.transcript_count === 1 ? 'transcript' : 'transcripts' }} · {{ formatCount(gene.pa_site_count) }} PAS
        </span>
        <span v-if="gene.disabledReason" class="picker-sr-only">{{ gene.disabledReason }}</span>
      </button>
    </div>
    <p v-if="showAll && !visibleCards.length" class="picker-capacity">No matching species or genes.</p>

    <p v-if="atCapacity" class="picker-capacity">
      {{ maxSelection }} genes selected — the comparison cap. Deselect one to add another.
    </p>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { formatCount } from '@/utils/pasLayout'

const props = defineProps({
  orthologSet: { type: Object, required: true },
  selectedIds: { type: Array, default: () => [] },
  maxSelection: { type: Number, default: 8 }
})

const emit = defineEmits(['update:selectedIds'])

const sourceId = computed(() => props.orthologSet.source_gene.gene_db_id)
const showAll = ref(false)
const search = ref('')
watch(sourceId, () => { showAll.value = false; search.value = '' })

const sourceDetailRoute = computed(() => ({
  name: 'GeneDetail',
  params: { geneId: sourceId.value },
  query: { species: props.orthologSet.source_gene.species }
}))

const atCapacity = computed(() => props.selectedIds.length >= props.maxSelection)

const SOURCE_REASON =
  'Source gene — always included in the comparison and cannot be deselected.'

const capacityReason = maxSelection =>
  `Cannot be added: the comparison is limited to ${maxSelection} genes. Deselect another gene first.`

const cards = computed(() =>
  [props.orthologSet.source_gene, ...props.orthologSet.orthologs].map(gene => {
    const selected = props.selectedIds.includes(gene.gene_db_id)
    const isSource = gene.gene_db_id === sourceId.value
    const blockedByCap = !selected && atCapacity.value
    return {
      ...gene,
      selected,
      isSource,
      disabled: isSource || blockedByCap,
      // The two reasons differ, so the announced explanation must differ too.
      disabledReason: isSource
        ? SOURCE_REASON
        : blockedByCap
          ? capacityReason(props.maxSelection)
          : ''
    }
  })
)

const visibleCards = computed(() => {
  if (!showAll.value) {
    const byId = new Map(cards.value.map(gene => [gene.gene_db_id, gene]))
    return props.selectedIds.map(id => byId.get(id)).filter(Boolean)
  }
  const query = search.value.trim().toLowerCase()
  return cards.value.filter(gene => `${gene.scientific_name} ${gene.gene_name} ${gene.gene_id}`.toLowerCase().includes(query))
})

const toggle = gene => {
  if (gene.disabled) return
  const next = gene.selected
    ? props.selectedIds.filter(id => id !== gene.gene_db_id)
    : [...props.selectedIds, gene.gene_db_id]
  emit('update:selectedIds', next)
}

/** Swallow Enter/Space on aria-disabled cards so they stay focusable but inert. */
const onKeydown = (event, gene) => {
  if (!gene.disabled) return
  if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
    event.preventDefault()
  }
}

const clearExtras = () => emit('update:selectedIds', [sourceId.value])
</script>

<style scoped>
.picker-card {
  padding: 24px;
  border-radius: var(--aa-radius-xl, 22px);
  overflow: hidden;
}

.picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.picker-head h2 {
  margin: 10px 0 7px;
  color: var(--aa-slate-800, #1e293b);
  font-size: var(--compare-title-size, 1.38rem);
  font-weight: 600;
  line-height: 1.3;
}
.picker-head p { margin: 0; color: var(--aa-slate-500); font-size: var(--compare-body-size); line-height: 1.55; }

.picker-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.picker-action {
  padding: 7px 13px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: var(--aa-radius-sm, 8px);
  background: #ffffff;
  color: var(--aa-slate-600, #475569);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}
.picker-action:hover:not(:disabled) {
  border-color: var(--aa-teal-600, #14919b);
  background: rgba(13, 115, 119, 0.08);
  color: var(--aa-teal-800, #0a5c5f);
}
.picker-action:disabled { opacity: 0.45; cursor: default; }
.picker-action--primary { color: #0d7377; border-color: #b9d9d9; background: #f2f9f9; }
.picker-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--aa-teal-700, #0d7377);
  font-size: 0.85rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.picker-link:hover { color: var(--aa-teal-800, #0a5c5f); text-decoration: underline; text-underline-offset: 3px; }

.picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
  margin-top: 18px;
}
.picker-grid--expanded { max-height: 350px; overflow-y: auto; padding: 3px; }
.picker-search { width: 100%; margin-top: 18px; padding: 10px 13px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; font-size: 0.9rem; color: #334155; background: #fff; }
.picker-search:focus-visible { outline: 2px solid #14919b; outline-offset: 2px; }

.picker-cardlet {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 14px 40px 14px 15px;
  border: 1px solid var(--aa-slate-200, #e2e8f0);
  border-radius: var(--aa-radius-md, 12px);
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.14s ease, background 0.14s ease;
}
.picker-cardlet:hover:not([aria-disabled='true']) {
  border-color: var(--aa-teal-600, #14919b);
  background: #f8fbfb;
}
.picker-cardlet:focus-visible {
  outline: 2px solid var(--aa-teal-600, #14919b);
  outline-offset: 2px;
}
.picker-cardlet.is-selected {
  border-color: var(--aa-teal-600, #14919b);
  background: var(--aa-teal-050, #effafa);
}
/* Still focusable — dim, but keep the text legible for keyboard users. */
.picker-cardlet[aria-disabled='true'] { cursor: default; }
.picker-cardlet[aria-disabled='true']:not(.is-selected) { opacity: 0.6; }

.picker-check {
  position: absolute;
  top: 13px;
  right: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  border: 1.5px solid var(--aa-slate-300, #cbd5e1);
  border-radius: 6px;
  background: #ffffff;
  color: #ffffff;
}
.is-selected .picker-check {
  border-color: var(--aa-teal-700, #0d7377);
  background: var(--aa-teal-700, #0d7377);
}

.picker-species { color: var(--aa-slate-600, #475569); font-size: 0.88rem; overflow-wrap: anywhere; }
.picker-gene {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--aa-slate-800, #1e293b);
  font-size: 1rem;
  font-weight: 600;
}
.picker-source-badge {
  padding: 2px 6px;
  border-radius: 5px;
  background: rgba(13, 115, 119, 0.12);
  color: var(--aa-teal-800, #0a5c5f);
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 600;
}
.picker-stats {
  margin-top: 6px;
  color: var(--aa-slate-500, #64748b);
  font-size: 0.82rem;
  font-weight: 400;
}
.picker-geneid { color: #64748b; font-size: 0.8rem; }

/* Visible to assistive technology only. */
.picker-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  border: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.picker-capacity {
  margin: 14px 0 0;
  color: var(--aa-slate-500, #64748b);
  font-size: 0.76rem;
}

@media (max-width: 960px) {
  .picker-card { padding: 20px; }
  .picker-head { flex-direction: column; }
}
@media (max-width: 640px) {
  .picker-grid { grid-template-columns: 1fr; }
  .picker-grid--expanded { max-height: 390px; }
}
</style>
