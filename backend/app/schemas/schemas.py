from pydantic import BaseModel
from typing import Optional, List, Union


class SpeciesBase(BaseModel):
    name: str
    latin_name: str
    assembly: Optional[str] = None
    tax_id: Optional[int] = None


class Species(SpeciesBase):
    id: int

    class Config:
        from_attributes = True


class CellLineBase(BaseModel):
    name: str
    species_id: int


class CellLine(CellLineBase):
    id: int
    species: Optional[Species] = None

    class Config:
        from_attributes = True


class GeneBase(BaseModel):
    gene_id: str
    gene_name: str
    chromosome: str
    strand: str
    species_id: int


class Gene(GeneBase):
    id: int

    class Config:
        from_attributes = True


class TranscriptBase(BaseModel):
    transcript_id: str
    gene_id: int
    species_id: int


class Transcript(TranscriptBase):
    id: int
    gene: Optional[Gene] = None

    class Config:
        from_attributes = True


class APASiteBase(BaseModel):
    unified_id: str
    transcript_id: int
    species_id: int
    mode_site_position: int
    transcript_biotype: Optional[str] = None
    representative_status: str = "not_representative"
    site_count: int = 0
    site_abundance: float = 0.0
    sample_data: Optional[str] = None
    cluster_start: Optional[int] = None
    cluster_end: Optional[int] = None
    sequence: Optional[str] = None
    pas_motif: Optional[str] = None
    pas_position: Optional[int] = None
    pas_type: Optional[str] = None
    search_level: Optional[str] = None
    pa_level: Optional[str] = None


class APASite(APASiteBase):
    id: int
    transcript: Optional[Transcript] = None
    species: Optional[Species] = None

    class Config:
        from_attributes = True


class APASiteWithDetails(APASiteBase):
    id: int
    transcript: Transcript
    species: Species
    sample_details: List[dict] = []

    class Config:
        from_attributes = True


class TranscriptWithGene(BaseModel):
    id: int
    transcript_id: str
    gene: GeneBase

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    transcript_id: str
    gene_id: str
    gene_db_id: int
    gene_name: str
    chromosome: str
    strand: str
    apa_site_count: int
    cell_lines: List[str]
    species: str

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    items: List[SearchResult]
    total: int


class DashboardStats(BaseModel):
    total_genes: int
    total_transcripts: int
    total_apa_sites: int
    total_cell_lines: int
    total_species: int
    apa_sites_by_species: List[dict]
    apa_sites_by_cell_line: List[dict]
    apa_sites_per_transcript: List[dict]
    apa_site_multiplicity: Optional[dict] = None


class LocusDetail(BaseModel):
    gene: Gene
    transcript: Transcript
    apa_sites: List[APASiteWithDetails]
    samples: List[Union[str, dict]]
    chromosomes: List[str]

    class Config:
        from_attributes = True


class GeneDetail(BaseModel):
    id: int
    gene_id: str
    gene_name: str
    chromosome: str
    strand: str
    species: Optional[str] = None
    transcripts: List[dict]

    class Config:
        from_attributes = True
