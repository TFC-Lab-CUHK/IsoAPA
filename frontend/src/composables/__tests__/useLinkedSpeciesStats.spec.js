import { describe, expect, it, vi } from 'vitest'
import { useLinkedSpeciesStats } from '../useLinkedSpeciesStats'

const deferred = () => {
  let resolve
  let reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

const fakeApi = () => Object.fromEntries([
  'getMultiplicityStats', 'getPasMotifStats', 'getTopGeneStats', 'getPasEvidenceStats'
].map(name => [name, vi.fn(async species => ({ species, name }))]))

describe('linked statistics species filter', () => {
  it('requests the same species for every panel and uses its recorded evidence cache', async () => {
    const api = fakeApi()
    const evidence = { species: 'Human', total_clusters: 12 }
    const state = useLinkedSpeciesStats(api, () => ({ pas_evidence_by_species: { Human: evidence } }))
    await state.selectSpecies('Human')
    expect(state.selectedSpecies.value).toBe('Human')
    for (const method of ['getMultiplicityStats', 'getPasMotifStats', 'getTopGeneStats']) {
      expect(api[method]).toHaveBeenCalledWith('Human')
    }
    expect(api.getPasEvidenceStats).not.toHaveBeenCalled()
    expect(state.results.value.evidence).toEqual(evidence)
  })

  it('loads evidence from the API if the species cache is unavailable', async () => {
    const api = fakeApi()
    const state = useLinkedSpeciesStats(api)
    await state.selectSpecies('Mouse')
    expect(api.getPasEvidenceStats).toHaveBeenCalledWith('Mouse')
    expect(state.results.value.evidence.species).toBe('Mouse')
  })

  it('does not mix late results from a previous selection with the current species', async () => {
    const api = fakeApi()
    const old = deferred()
    for (const method of Object.keys(api)) {
      api[method].mockImplementation(species => species === 'Human' ? old.promise : Promise.resolve({ species }))
    }
    const state = useLinkedSpeciesStats(api)
    const first = state.selectSpecies('Human')
    await state.selectSpecies('Mouse')
    old.resolve({ species: 'Human' })
    await first
    expect(state.selectedSpecies.value).toBe('Mouse')
    for (const result of Object.values(state.results.value)) expect(result.species).toBe('Mouse')
    expect(state.loading.value).toBe(false)
  })

  it('clears old values and waits for all panels before displaying a new selection', async () => {
    const api = fakeApi()
    const state = useLinkedSpeciesStats(api)
    await state.selectSpecies('Human')
    const slow = deferred()
    api.getTopGeneStats.mockReturnValueOnce(slow.promise)
    const update = state.selectSpecies('Mouse')
    await Promise.resolve()
    expect(state.loading.value).toBe(true)
    expect(Object.values(state.results.value).every(value => value === null)).toBe(true)
    slow.resolve({ species: 'Mouse' })
    await update
    for (const result of Object.values(state.results.value)) expect(result.species).toBe('Mouse')
  })

  it('returns All species without incorrectly retaining a species-specific evidence summary', async () => {
    const api = fakeApi()
    const state = useLinkedSpeciesStats(api)
    await state.selectSpecies('Human')
    api.getPasEvidenceStats.mockClear()
    await state.selectSpecies('')
    expect(state.results.value.evidence).toBeNull()
    expect(api.getPasEvidenceStats).not.toHaveBeenCalled()
    expect(api.getMultiplicityStats).toHaveBeenLastCalledWith(undefined)
    expect(api.getPasMotifStats).toHaveBeenLastCalledWith(undefined)
    expect(api.getTopGeneStats).toHaveBeenLastCalledWith(undefined)
  })

  it('reports a failed panel instead of substituting global results, and supports retry', async () => {
    const api = fakeApi()
    api.getMultiplicityStats.mockRejectedValueOnce(new Error('unavailable'))
    const state = useLinkedSpeciesStats(api)
    await state.selectSpecies('Mouse')
    expect(state.results.value.multiplicity).toBeNull()
    expect(state.errors.value.multiplicity).toBe(true)
    expect(state.results.value.motif.species).toBe('Mouse')
    await state.selectSpecies('Mouse')
    expect(state.results.value.multiplicity.species).toBe('Mouse')
    expect(state.errors.value.multiplicity).toBe(false)
  })

  it('ignores in-flight results after the view has been disposed', async () => {
    const api = fakeApi()
    const pending = deferred()
    api.getMultiplicityStats.mockReturnValueOnce(pending.promise)
    const state = useLinkedSpeciesStats(api)
    const update = state.selectSpecies('Human')
    state.dispose()
    pending.resolve({ species: 'Human' })
    await update
    expect(Object.values(state.results.value).every(value => value === null)).toBe(true)
  })

  it('shows cached global panels immediately while refreshing them, never under a species label', async () => {
    const api = fakeApi()
    const pending = deferred()
    api.getMultiplicityStats.mockImplementation(species => species ? Promise.resolve({ species }) : pending.promise)
    const cache = {
      apa_site_multiplicity: { total: 100 },
      pas_motif_distribution: { all: { total: 20 } },
      top_genes_by_apa: [{ gene_name: 'Cached gene' }]
    }
    const state = useLinkedSpeciesStats(api, () => cache)
    const initial = state.reload()
    expect(state.results.value.multiplicity.total).toBe(100)
    expect(state.results.value.motif.total).toBe(20)
    expect(state.loading.value).toBe(true)
    const selected = state.selectSpecies('Mouse')
    expect(state.results.value.multiplicity).toBeNull()
    await selected
    pending.resolve({ total: 101 })
    await initial
    expect(state.results.value.multiplicity.species).toBe('Mouse')
    expect(cache.apa_site_multiplicity.total).toBe(100)
  })
})
