from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    Index,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, deferred
from app.config import settings

Base = declarative_base()


class Species(Base):
    __tablename__ = "species"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    latin_name = Column(String(100), nullable=False)
    assembly = Column(String(100), nullable=True)
    tax_id = Column(Integer, nullable=True, index=True)
    motif_model = Column(String(40), nullable=True)

    samples = relationship("Sample", back_populates="species")
    apa_sites = relationship("APASite", back_populates="species")


class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    sample_type = Column(String(50), nullable=False, default="cell_culture")
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)

    species = relationship("Species", back_populates="samples")

    __table_args__ = (Index("idx_sample_species", "name", "species_id", unique=True),)


class Gene(Base):
    __tablename__ = "genes"

    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(String(100), nullable=False, index=True)
    gene_key = Column(String(300), nullable=False, index=True)
    gene_name = Column(String(100), nullable=False, index=True)
    chromosome = Column(String(50), nullable=False, index=True)
    strand = Column(String(1), nullable=False)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False, index=True)

    transcripts = relationship("Transcript", back_populates="gene")

    __table_args__ = (
        Index("idx_gene_name", "gene_name"),
        Index("idx_gene_species", "gene_key", "species_id", unique=True),
    )


class OrthologRelation(Base):
    __tablename__ = "ortholog_relations"

    id = Column(Integer, primary_key=True)
    gene_a_id = Column(Integer, ForeignKey("genes.id"), nullable=False, index=True)
    gene_b_id = Column(Integer, ForeignKey("genes.id"), nullable=False, index=True)
    relationship = Column(String(30), nullable=False, default="Ortholog")
    source = Column(String(80), nullable=False, default="NCBI Gene orthologs")

    __table_args__ = (
        Index(
            "idx_ortholog_pair_source",
            "gene_a_id",
            "gene_b_id",
            "source",
            unique=True,
        ),
    )


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    transcript_id = Column(String(100), nullable=False, index=True)
    gene_id = Column(Integer, ForeignKey("genes.id"), nullable=False)
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False, index=True)

    gene = relationship("Gene", back_populates="transcripts")
    apa_sites = relationship("APASite", back_populates="transcript")

    __table_args__ = (
        Index("idx_transcript_species", "transcript_id", "species_id", unique=True),
        Index("idx_transcript_gene", "gene_id"),
    )


class APASite(Base):
    __tablename__ = "apa_sites"

    id = Column(Integer, primary_key=True, index=True)
    unified_id = Column(String(300), nullable=False, index=True)
    transcript_id = Column(
        Integer, ForeignKey("transcripts.id"), nullable=False, index=True
    )
    species_id = Column(Integer, ForeignKey("species.id"), nullable=False)

    mode_site_position = Column(Integer, nullable=False, index=True)
    transcript_biotype = Column(String(50), nullable=True)
    representative_status = Column(
        String(30), nullable=False, default="not_representative"
    )

    site_count = Column(Integer, nullable=False, default=0)
    site_abundance = Column(Float, nullable=False, default=0.0)
    # Kept nullable for old SQLite files; application code uses apa_site_samples.
    sample_data = Column(Text, nullable=True)

    cluster_start = Column(Integer, nullable=True)
    cluster_end = Column(Integer, nullable=True)

    sequence = deferred(Column(String(200), nullable=True))
    pas_motif = deferred(Column(String(10), nullable=True))
    pas_position = deferred(Column(Integer, nullable=True))
    pas_type = deferred(Column(String(30), nullable=True))
    search_level = deferred(Column(String(20), nullable=True))
    pa_level = deferred(Column(String(30), nullable=True))

    transcript = relationship("Transcript", back_populates="apa_sites")
    species = relationship("Species", back_populates="apa_sites")
    sample_observations = relationship("APASiteSample", back_populates="apa_site")

    __table_args__ = (
        Index(
            "idx_apa_species_transcript_unified_id",
            "species_id",
            "transcript_id",
            "unified_id",
            unique=True,
        ),
    )


class APASiteSample(Base):
    __tablename__ = "apa_site_samples"

    id = Column(Integer, primary_key=True)
    apa_site_id = Column(Integer, ForeignKey("apa_sites.id"), nullable=False, index=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False, index=True)
    sample_order = Column(Integer, nullable=False, default=0)
    original_site_position = Column(Integer, nullable=False)
    site_count = Column(Integer, nullable=False, default=0)
    site_abundance = Column(Float, nullable=False, default=0.0)

    apa_site = relationship("APASite", back_populates="sample_observations")
    sample = relationship("Sample")

    __table_args__ = (
        Index("idx_apa_site_sample", "apa_site_id", "sample_id"),
        Index("idx_apa_site_sample_order", "apa_site_id", "sample_order"),
    )


class TranscriptSearchIndex(Base):
    __tablename__ = "transcript_search_index"

    id = Column(Integer, primary_key=True)
    transcript_db_id = Column(Integer, nullable=False, unique=True, index=True)
    transcript_id = Column(String(100), nullable=False, index=True)
    gene_id = Column(String(100), nullable=False, index=True)
    gene_db_id = Column(Integer, nullable=False, index=True)
    gene_name = Column(String(100), nullable=False, index=True)
    gene_name_lc = Column(String(100), nullable=False, index=True)
    chromosome = Column(String(50), nullable=False, index=True)
    strand = Column(String(1), nullable=False)
    species = Column(String(100), nullable=False, index=True)
    species_id = Column(Integer, nullable=False, index=True)
    apa_site_count = Column(Integer, nullable=False, default=0, index=True)

    __table_args__ = (
        Index("idx_tsi_default_order", "gene_name", "transcript_id", "species"),
        Index("idx_tsi_gene_species", "gene_name_lc", "species"),
        Index("idx_tsi_gene_default_order", "gene_name_lc", "gene_name", "transcript_id", "species"),
        Index("idx_tsi_species_default_order", "species", "gene_name", "transcript_id"),
        Index("idx_tsi_transcript_species", "transcript_id", "species"),
        Index("idx_tsi_species_gene", "species", "gene_name_lc"),
        Index("idx_tsi_species_apa", "species", "apa_site_count"),
    )


class TranscriptSearchSample(Base):
    __tablename__ = "transcript_search_samples"

    id = Column(Integer, primary_key=True)
    transcript_db_id = Column(Integer, nullable=False, index=True)
    sample_id = Column(Integer, nullable=False, index=True)
    sample_name = Column(String(100), nullable=False, index=True)
    sample_name_lc = Column(String(100), nullable=False, index=True)
    species_id = Column(Integer, nullable=False, index=True)
    apa_site_count = Column(Integer, nullable=False, default=0, index=True)

    __table_args__ = (
        Index("idx_tss_sample_transcript", "sample_name_lc", "transcript_db_id"),
        Index("idx_tss_sample_count", "sample_name_lc", "apa_site_count"),
        Index("idx_tss_transcript_sample", "transcript_db_id", "sample_name"),
    )


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.DATABASE_URL
    else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
