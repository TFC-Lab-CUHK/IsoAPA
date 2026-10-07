from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import (
    APASite,
    APASiteSample,
    Gene,
    Sample,
    Species,
    Transcript,
    TranscriptSearchIndex,
    TranscriptSearchSample,
)


def rebuild_search_index(db: Session, species_ids: list[int] | None = None) -> None:
    """Materialize transcript-level search metadata for fast browse/search."""
    if species_ids is not None and not species_ids:
        return
    sample_index = db.query(TranscriptSearchSample)
    transcript_index = db.query(TranscriptSearchIndex)
    if species_ids is not None:
        sample_index = sample_index.filter(TranscriptSearchSample.species_id.in_(species_ids))
        transcript_index = transcript_index.filter(TranscriptSearchIndex.species_id.in_(species_ids))
    sample_index.delete(synchronize_session=False)
    transcript_index.delete(synchronize_session=False)
    db.commit()

    transcript_rows = (
        db.query(
            Transcript.id.label("transcript_db_id"),
            Transcript.transcript_id,
            Gene.gene_id,
            Gene.id.label("gene_db_id"),
            Gene.gene_name,
            Gene.chromosome,
            Gene.strand,
            Species.name.label("species"),
            Species.id.label("species_id"),
            func.count(APASite.id).label("apa_site_count"),
        )
        .select_from(Transcript)
        .join(Gene, Transcript.gene_id == Gene.id)
        .join(Species, Transcript.species_id == Species.id)
        .join(APASite, APASite.transcript_id == Transcript.id)
        .group_by(
            Transcript.id,
            Transcript.transcript_id,
            Gene.gene_id,
            Gene.id,
            Gene.gene_name,
            Gene.chromosome,
            Gene.strand,
            Species.name,
            Species.id,
        )
    )

    if species_ids is not None:
        transcript_rows = transcript_rows.filter(Transcript.species_id.in_(species_ids))

    batch = []
    for row in transcript_rows.yield_per(5000):
        batch.append(
            {
                "transcript_db_id": row.transcript_db_id,
                "transcript_id": row.transcript_id,
                "gene_id": row.gene_id,
                "gene_db_id": row.gene_db_id,
                "gene_name": row.gene_name,
                "gene_name_lc": (row.gene_name or "").lower(),
                "chromosome": row.chromosome,
                "strand": row.strand,
                "species": row.species,
                "species_id": row.species_id,
                "apa_site_count": row.apa_site_count or 0,
            }
        )
        if len(batch) >= 5000:
            db.bulk_insert_mappings(TranscriptSearchIndex, batch)
            db.commit()
            batch = []

    if batch:
        db.bulk_insert_mappings(TranscriptSearchIndex, batch)
        db.commit()

    sample_rows = (
        db.query(
            APASite.transcript_id.label("transcript_db_id"),
            Sample.id.label("sample_id"),
            Sample.name.label("sample_name"),
            Sample.species_id.label("species_id"),
            func.count(APASite.id).label("apa_site_count"),
        )
        .select_from(APASite)
        .join(APASiteSample, APASiteSample.apa_site_id == APASite.id)
        .join(Sample, APASiteSample.sample_id == Sample.id)
        .group_by(APASite.transcript_id, Sample.id, Sample.name, Sample.species_id)
    )

    if species_ids is not None:
        sample_rows = sample_rows.filter(APASite.species_id.in_(species_ids))

    batch = []
    for row in sample_rows.yield_per(10000):
        batch.append(
            {
                "transcript_db_id": row.transcript_db_id,
                "sample_id": row.sample_id,
                "sample_name": row.sample_name,
                "sample_name_lc": (row.sample_name or "").lower(),
                "species_id": row.species_id,
                "apa_site_count": row.apa_site_count or 0,
            }
        )
        if len(batch) >= 10000:
            db.bulk_insert_mappings(TranscriptSearchSample, batch)
            db.commit()
            batch = []

    if batch:
        db.bulk_insert_mappings(TranscriptSearchSample, batch)
        db.commit()


def ensure_search_index(db: Session) -> None:
    if db.query(TranscriptSearchIndex.id).limit(1).first():
        return
    rebuild_search_index(db)


if __name__ == "__main__":
    from app.models.database import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        rebuild_search_index(session)
