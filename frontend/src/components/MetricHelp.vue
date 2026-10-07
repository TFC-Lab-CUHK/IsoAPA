<template>
  <v-tooltip
    location="top"
    max-width="320"
    content-class="metric-help-tooltip"
    :text="definition.text"
    :open-on-hover="hoverCapable"
    :open-on-click="!hoverCapable"
    :open-on-focus="true"
  >
    <template #activator="{ props }">
      <button
        type="button"
        class="metric-help-button"
        :aria-label="`About ${definition.label}`"
        v-bind="props"
        @click.stop
      >
        <v-icon icon="mdi-help-circle-outline" size="14" />
      </button>
    </template>
  </v-tooltip>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

defineProps({ definition: { type: Object, required: true } })

const hoverQuery = typeof window !== 'undefined' ? window.matchMedia('(hover: hover)') : null
const hoverCapable = ref(hoverQuery?.matches ?? true)
const updateHover = event => { hoverCapable.value = event.matches }
onMounted(() => hoverQuery?.addEventListener('change', updateHover))
onUnmounted(() => hoverQuery?.removeEventListener('change', updateHover))
</script>

<style scoped>
.metric-help-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 3px;
  padding: 0;
  flex-shrink: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #64748b;
  vertical-align: middle;
  cursor: help;
}
.metric-help-button:hover { color: #0d7377; }
.metric-help-button:focus-visible { outline: 2px solid #0d7377; outline-offset: 2px; }
:global(.v-tooltip > .v-overlay__content.metric-help-tooltip) {
  background: #f8fafc;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 13px;
  font-family: var(--aa-font-sans);
  font-size: 12.5px;
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: normal;
  text-transform: none;
}
</style>
