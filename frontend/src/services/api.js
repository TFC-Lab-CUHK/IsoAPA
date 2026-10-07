import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

export const apiService = {
  async getDetailedStats() {
    const response = await api.get('/stats/detailed')
    return response.data
  },

  async getMultiplicityStats(species) {
    const response = await api.get('/stats/multiplicity', { params: { species } })
    return response.data
  },

  async getPasMotifStats(species) {
    const response = await api.get('/stats/pas-motifs', { params: { species } })
    return response.data
  },

  async getPasEvidenceStats(species) {
    const response = await api.get('/stats/pas-evidence', { params: { species } })
    return response.data
  },

  async getTopGeneStats(species) {
    const response = await api.get('/stats/top-genes', { params: { species } })
    return response.data
  },
  
  async search(params) {
    const response = await api.get('/search', { params })
    return response.data
  },

  async searchOrthologGenes(species, q, limit = 20) {
    const response = await api.get('/orthologs/search', {
      params: { species, q, limit }
    })
    return response.data
  },

  async getGeneOrthologs(geneDbId) {
    const response = await api.get(`/orthologs/${geneDbId}`)
    return response.data
  },

  async compareOrthologGenes(geneIds, maxTranscripts = 12) {
    const response = await api.get('/orthologs/compare', {
      params: {
        gene_ids: geneIds.join(','),
        max_transcripts: maxTranscripts
      }
    })
    return response.data
  },
  
  async autocomplete(q, field, limit = 30) {
    const response = await api.get('/autocomplete', { params: { q, field, limit } })
    return response.data
  },
  
  async getLocusDetail(transcriptId, species) {
    const response = await api.get(`/transcript/${transcriptId}`, { params: { species } })
    return response.data
  },
  
  async getGeneDetail(geneId, species) {
    const response = await api.get(`/gene/${geneId}`, { params: { species } })
    return response.data
  },

  async getGeneSummary(geneId, species) {
    const response = await api.get(`/gene/${geneId}/summary`, { params: { species } })
    return response.data
  },
  
  async getTranscriptStructure(transcriptId, species) {
    const response = await api.get(`/transcript/${transcriptId}/structure`, { params: { species } })
    return response.data
  },
  
  async getSpecies() {
    const response = await api.get('/species')
    return response.data
  },
  
  async getSamples(species) {
    const response = await api.get('/samples', { params: { species } })
    return response.data
  },
  
  async getSiteSequence(transcriptId, siteId, flank = 50, species) {
    const response = await api.get(
      `/transcript/${transcriptId}/site-sequence/${encodeURIComponent(siteId)}`,
      { params: { flank, species } }
    )
    return response.data
  }
}

export default api
