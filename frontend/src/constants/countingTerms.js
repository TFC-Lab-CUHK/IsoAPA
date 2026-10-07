export const COUNT_TERMS = {
  pasClusters: {
    label: 'PAS clusters',
    text: 'Each unified PAS cluster is counted once per species, across all transcripts and sample groups.'
  },
  transcriptPasRecords: {
    label: 'Transcript-PAS records',
    text: 'One record per transcript-PAS association across sample groups. Shared PASs contribute a record for each associated transcript.'
  },
  sampleObservations: {
    label: 'Sample observations',
    text: 'One recorded PAS observation for a transcript in a sample group.'
  },
  sampleGroups: {
    label: 'Sample groups',
    text: 'Sequencing runs grouped by species and harmonised sample name. Groups are not necessarily independent biological replicates.'
  },
  isoforms: {
    label: 'Isoforms',
    text: 'Observed reference transcripts, counted once within each species across sample groups.'
  },
  multiplicity: {
    label: 'PAS multiplicity',
    text: 'Distinct PASs observed for each transcript across all available sample groups. They may be detected in different sample groups.'
  },
  meanPas: {
    label: 'Mean PASs per isoform',
    text: 'Count distinct PASs across all sample groups for each transcript, then average across transcripts. Shared PASs count for each transcript.'
  },
  meanIsoforms: {
    label: 'Mean isoforms per gene',
    text: 'Observed transcript count divided by the number of represented gene entries.'
  },
  genePasClusters: {
    label: 'Gene PAS counts',
    text: 'Unique PAS clusters per gene, counted once across its transcripts and sample groups.'
  },
  motifCounts: {
    label: 'PAS motif counts',
    text: 'Motifs are counted once per unified PAS cluster. Not assessed denotes species without a supported motif model.'
  },
  abundanceMatrix: {
    label: 'Matrix rows and columns',
    text: 'Rows are transcript-PAS associations; columns give supporting read counts and relative usage for each sample group.'
  }
}
