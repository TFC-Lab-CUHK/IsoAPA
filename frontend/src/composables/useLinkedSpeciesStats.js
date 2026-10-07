import { ref } from 'vue'

const emptyResults = () => ({ multiplicity: null, motif: null, evidence: null, genes: null })

export const useLinkedSpeciesStats = (api, cachedStats = () => ({})) => {
  const selectedSpecies = ref('')
  const loading = ref(false)
  const results = ref(emptyResults())
  const errors = ref({})
  let requestId = 0
  let disposed = false

  const reload = async () => {
    if (disposed) return
    const id = ++requestId
    const species = selectedSpecies.value
    const cache = cachedStats() || {}
    results.value = emptyResults()
    // A global snapshot can be shown during refresh, never under a species label.
    if (!species) {
      results.value = {
        multiplicity: cache.apa_site_multiplicity || null,
        motif: cache.pas_motif_distribution?.all || null,
        genes: cache.top_genes_by_apa?.slice(0, 10) || null,
        evidence: null
      }
    }
    errors.value = {}
    loading.value = true

    const requests = {
      multiplicity: () => api.getMultiplicityStats(species || undefined),
      motif: () => api.getPasMotifStats(species || undefined),
      genes: () => api.getTopGeneStats(species || undefined),
      evidence: () => species
        ? (cache.pas_evidence_by_species?.[species] ?? api.getPasEvidenceStats(species))
        : null
    }
    const keys = Object.keys(requests)
    const responses = await Promise.allSettled(keys.map(key => Promise.resolve().then(requests[key])))
    if (disposed || id !== requestId || species !== selectedSpecies.value) return

    // Commit the four results together, only for the current selection.
    results.value = Object.fromEntries(keys.map((key, index) => [
      key, responses[index].status === 'fulfilled' ? responses[index].value : null
    ]))
    errors.value = Object.fromEntries(keys.map((key, index) => [key, responses[index].status === 'rejected']))
    loading.value = false
  }

  const selectSpecies = async species => {
    const next = species || ''
    if (next === selectedSpecies.value && !Object.values(errors.value).some(Boolean)) return
    selectedSpecies.value = next
    await reload()
  }

  const dispose = () => { disposed = true; requestId += 1 }
  return { selectedSpecies, loading, results, errors, selectSpecies, reload, dispose }
}
