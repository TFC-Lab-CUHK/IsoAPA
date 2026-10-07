export const formatSampleName = (name) =>
  String(name ?? '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

export const formatSampleType = (type) =>
  formatSampleName(type).replace(/\b\w/g, c => c.toUpperCase())

const FORMAL_SPECIES_NAMES = {
  Human: 'Homo sapiens',
  Mouse: 'Mus musculus',
}

export const formatSpeciesName = (species) => {
  if (species && typeof species === 'object') {
    const rawName = species.name ?? ''
    const latinName = species.latin_name ?? ''
    const preferredName =
      species.display_name ||
      FORMAL_SPECIES_NAMES[rawName] ||
      (latinName && latinName !== rawName ? latinName : rawName || latinName)

    return String(preferredName ?? '').replace(/_/g, ' ')
  }

  const rawName = String(species ?? '')
  return String(FORMAL_SPECIES_NAMES[rawName] || rawName).replace(/_/g, ' ')
}

export const formatSpeciesSubtitle = (species) => {
  if (!species || typeof species !== 'object') return ''

  const displayName = formatSpeciesName(species)
  const latinName = String(species.latin_name ?? '').replace(/_/g, ' ')
  return latinName && latinName !== displayName ? latinName : ''
}
