import json
import os
from datetime import datetime, timezone

from sqlalchemy import case, func

from app.models.database import (
    APASite,
    APASiteSample,
    Gene,
    Sample,
    SessionLocal,
    Species,
    Transcript,
)
from app.services.pas_motif_stats import PRIMARY_PAS_TYPES, summarize_pas_motif_rows
from app.services.pas_evidence_stats import build_pas_evidence_cache


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATS_CACHE_FILE = os.path.join(BACKEND_DIR, "stats_cache.json")


def _format_sample_name(name: str) -> str:
    return str(name or "").replace("_", " ")


def _format_species_name(name: str, latin_name: str | None = None) -> str:
    formal_names = {
        "Human": "Homo sapiens",
        "Mouse": "Mus musculus",
    }
    if name in formal_names:
        return formal_names[name]

    preferred = latin_name if latin_name and latin_name != name else name
    return str(preferred or "").replace("_", " ")


def _multiplicity_bucket(count: int) -> str:
    if count >= 5:
        return "5+"
    return str(max(count, 0))


def _summarize_pas_motif_rows(rows) -> dict:
    return summarize_pas_motif_rows(rows)


def _count_distinct_species_sites(db) -> int:
    species_sites = (
        db.query(APASite.species_id, APASite.unified_id).distinct().subquery()
    )
    return db.query(func.count()).select_from(species_sites).scalar() or 0


def _build_pas_motif_cache(db) -> dict:
    motif_rank = case(
        (APASite.pas_type.in_(PRIMARY_PAS_TYPES), 1),
        (APASite.pas_type == "not_assessed", 4),
        (APASite.pas_motif.is_(None), 3),
        (APASite.pas_motif == "", 3),
        else_=2,
    )

    all_site_choice = db.query(
        APASite.species_id.label("species_id"),
        APASite.unified_id.label("site_id"),
        APASite.pas_motif.label("motif"),
        APASite.pas_type.label("motif_type"),
        func.row_number()
        .over(
            partition_by=[APASite.species_id, APASite.unified_id],
            order_by=motif_rank,
        )
        .label("rn"),
    ).subquery()

    all_rows = (
        db.query(
            all_site_choice.c.motif,
            all_site_choice.c.motif_type,
            func.count(all_site_choice.c.site_id).label("site_count"),
        )
        .filter(all_site_choice.c.rn == 1)
        .group_by(all_site_choice.c.motif, all_site_choice.c.motif_type)
        .all()
    )

    species_site_choice = (
        db.query(
            Species.name.label("species"),
            APASite.unified_id.label("site_id"),
            APASite.pas_motif.label("motif"),
            APASite.pas_type.label("motif_type"),
            func.row_number()
            .over(partition_by=[Species.name, APASite.unified_id], order_by=motif_rank)
            .label("rn"),
        )
        .join(Species, APASite.species_id == Species.id)
        .subquery()
    )

    species_rows = (
        db.query(
            species_site_choice.c.species,
            species_site_choice.c.motif,
            species_site_choice.c.motif_type,
            func.count(species_site_choice.c.site_id).label("site_count"),
        )
        .filter(species_site_choice.c.rn == 1)
        .group_by(
            species_site_choice.c.species,
            species_site_choice.c.motif,
            species_site_choice.c.motif_type,
        )
        .all()
    )

    rows_by_species: dict[str, list] = {}
    for species, motif, motif_type, count in species_rows:
        rows_by_species.setdefault(species, []).append((motif, motif_type, count))

    return {
        "all": _summarize_pas_motif_rows(all_rows),
        "by_species": {
            species: _summarize_pas_motif_rows(rows)
            for species, rows in rows_by_species.items()
        },
    }


def build_stats_cache(output_path: str = STATS_CACHE_FILE) -> dict:
    db = SessionLocal()
    try:
        total_genes = db.query(Gene).count()
        total_transcripts = db.query(Transcript).count()
        total_apa_sites = _count_distinct_species_sites(db)
        total_samples = db.query(Sample).count()
        total_species = db.query(Species).count()

        species_lookup = {
            s.name: s for s in db.query(Species).all()
        }
        distinct_site_count = func.count(func.distinct(APASite.unified_id))

        apa_by_species = (
            db.query(Species.name, distinct_site_count.label("count"))
            .select_from(APASite)
            .join(Species, APASite.species_id == Species.id)
            .group_by(Species.name)
            .all()
        )

        apa_by_chromosome = (
            db.query(Gene.chromosome, func.count(APASite.id).label("count"))
            .select_from(APASite)
            .join(Transcript, APASite.transcript_id == Transcript.id)
            .join(Gene, Transcript.gene_id == Gene.id)
            .filter(Gene.chromosome.isnot(None))
            .group_by(Gene.chromosome)
            .order_by(Gene.chromosome)
            .all()
        )

        apa_by_strand = (
            db.query(Gene.strand, func.count(APASite.id).label("count"))
            .select_from(APASite)
            .join(Transcript, APASite.transcript_id == Transcript.id)
            .join(Gene, Transcript.gene_id == Gene.id)
            .filter(Gene.strand.isnot(None))
            .group_by(Gene.strand)
            .all()
        )

        top_genes = (
            db.query(
                Gene.gene_name,
                Gene.gene_id,
                Species.name.label("species"),
                distinct_site_count.label("apa_count"),
                Gene.id,
            )
            .select_from(APASite)
            .join(Transcript, APASite.transcript_id == Transcript.id)
            .join(Gene, Transcript.gene_id == Gene.id)
            .join(Species, Gene.species_id == Species.id)
            .group_by(Gene.gene_name, Gene.gene_id, Species.name, Gene.id)
            .order_by(distinct_site_count.desc())
            .limit(20)
            .all()
        )

        count_per_transcript = (
            db.query(Transcript.id, func.count(func.distinct(APASite.unified_id)).label("apa_count"))
            .outerjoin(APASite, APASite.transcript_id == Transcript.id)
            .group_by(Transcript.id)
            .subquery()
        )
        avg_result = db.query(func.avg(count_per_transcript.c.apa_count)).scalar()
        avg_apa_per_transcript = float(avg_result) if avg_result else 0

        multiplicity_rows = db.query(count_per_transcript.c.apa_count).all()
        multiplicity_buckets = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
        multi_count = 0
        single_count = 0
        for (count,) in multiplicity_rows:
            count = int(count or 0)
            multiplicity_buckets[_multiplicity_bucket(count)] += 1
            if count == 1:
                single_count += 1
            if count >= 2:
                multi_count += 1
        multiplicity_total = len(multiplicity_rows)
        pas_motif_distribution = _build_pas_motif_cache(db)

        sample_counts = {
            _format_sample_name(sample_name): count
            for sample_name, count in (
                db.query(Sample.name, func.count(APASiteSample.id))
                .join(APASiteSample, APASiteSample.sample_id == Sample.id)
                .group_by(Sample.name)
                .all()
            )
        }

        detailed = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_genes": total_genes,
            "total_transcripts": total_transcripts,
            "total_apa_sites": total_apa_sites,
            "total_samples": total_samples,
            "total_species": total_species,
            "avg_apa_per_transcript": round(avg_apa_per_transcript, 2),
            "avg_isoforms_per_gene": round(total_transcripts / total_genes, 2) if total_genes else 0,
            "apa_sites_by_species": [
                {
                    "name": name,
                    "display_name": _format_species_name(
                        name, species_lookup.get(name).latin_name if species_lookup.get(name) else None
                    ),
                    "count": count,
                }
                for name, count in apa_by_species
            ],
            "apa_sites_by_sample": [
                {"name": name, "count": count}
                for name, count in sorted(sample_counts.items(), key=lambda item: item[1], reverse=True)
            ],
            "apa_sites_by_chromosome": [
                {"chromosome": chromosome, "count": count}
                for chromosome, count in apa_by_chromosome
            ],
            "apa_sites_by_strand": [
                {"strand": strand, "count": count}
                for strand, count in apa_by_strand
            ],
            "top_genes_by_apa": [
                {
                    "gene_name": gene_name,
                    "gene_id": gene_id,
                    "species": species,
                    "apa_count": apa_count,
                    "gene_db_id": gene_db_id,
                }
                for gene_name, gene_id, species, apa_count, gene_db_id in top_genes
            ],
            "apa_site_multiplicity": {
                "buckets": multiplicity_buckets,
                "total": multiplicity_total,
                "single_site_count": single_count,
                "multi_site_count": multi_count,
                "pct_single_site": round((single_count / multiplicity_total) * 100, 1) if multiplicity_total else 0,
                "pct_multi_site": round((multi_count / multiplicity_total) * 100, 1) if multiplicity_total else 0,
            },
            "pas_motif_distribution": pas_motif_distribution,
            "pas_evidence_by_species": build_pas_evidence_cache(db),
        }

        basic = {
            "total_genes": total_genes,
            "total_transcripts": total_transcripts,
            "total_apa_sites": total_apa_sites,
            "total_cell_lines": total_samples,
            "total_species": total_species,
            "apa_sites_by_species": detailed["apa_sites_by_species"],
            "apa_sites_by_cell_line": detailed["apa_sites_by_sample"],
            "apa_site_multiplicity": detailed["apa_site_multiplicity"],
            "apa_sites_per_transcript": [],
        }

        payload = {"basic": basic, "detailed": detailed}
        tmp_path = output_path + ".tmp"
        with open(tmp_path, "w") as fh:
            json.dump(payload, fh, separators=(",", ":"))
        os.replace(tmp_path, output_path)
        return payload
    finally:
        db.close()


if __name__ == "__main__":
    stats = build_stats_cache()
    detailed = stats["detailed"]
    print(
        "Stats cache ready: "
        f"{detailed['total_species']:,} species, "
        f"{detailed['total_transcripts']:,} transcripts, "
        f"{detailed['total_apa_sites']:,} PA sites"
    )
