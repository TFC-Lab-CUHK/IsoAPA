<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    style="display:inline-block;vertical-align:middle;flex-shrink:0"
  >
    <!-- 5' spine (shared gene start) -->
    <line x1="4" y1="5" x2="4" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <!-- Isoform 1 — distal site (longest 3' UTR) -->
    <line x1="4" y1="8" x2="20" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="20" cy="8" r="2" fill="currentColor"/>
    <!-- Isoform 2 — middle site -->
    <line x1="4" y1="12" x2="14" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="14" cy="12" r="2" fill="currentColor"/>
    <!-- Isoform 3 — proximal site (shortest 3' UTR) -->
    <line x1="4" y1="16" x2="9" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="9" cy="16" r="2" fill="currentColor"/>
  </svg>
</template>

<script setup>
defineProps({
  size: { type: [Number, String], default: 24 },
})
</script>
