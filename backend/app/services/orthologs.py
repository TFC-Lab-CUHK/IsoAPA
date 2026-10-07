"""Offline NCBI Gene ortholog indexing for cross-species comparisons."""

from __future__ import annotations

import csv
import gzip
import os
import shutil
from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.database import Gene, OrthologRelation, Species


NCBI_GENE_ORTHOLOG_URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_orthologs.gz"
ORTHOLOG_SOURCE_NAME = "NCBI Gene orthologs"
TAXONOMY_RESOURCE = (
    Path(__file__).resolve().parents[1] / "resources" / "species_taxonomy.tsv"
)


def _name_key(value: str | None) -> str:
    return " ".join(str(value or "").replace("_", " ").casefold().split())


@lru_cache(maxsize=1)
def load_species_taxonomy() -> dict[str, dict]:
    by_key: dict[str, dict] = {}
    with TAXONOMY_RESOURCE.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            record = {
                "species_key": row["species_key"],
                "tax_id": int(row["tax_id"]),
                "scientific_name": row["scientific_name"],
            }
            by_key[_name_key(row["species_key"])] = record
            by_key[_name_key(row["scientific_name"])] = record
    return by_key


def taxonomy_record_for_species(
    species_key: str | None,
    scientific_name: str | None = None,
) -> dict | None:
    taxonomy = load_species_taxonomy()
    for value in (species_key, scientific_name):
        record = taxonomy.get(_name_key(value))
        if record:
            return record
    return None


def ensure_species_taxids(db: Session, species_ids: list[int] | None = None) -> int:
    updated = 0
    query = db.query(Species)
    if species_ids is not None:
        query = query.filter(Species.id.in_(species_ids))
    for species in query.all():
        record = taxonomy_record_for_species(species.name, species.latin_name)
        if record and species.tax_id != record["tax_id"]:
            species.tax_id = record["tax_id"]
            updated += 1
    if updated:
        db.flush()
    return updated


def default_ortholog_cache_path() -> Path:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "isoapa" / "ncbi" / "gene_orthologs.gz"


def _download_ortholog_source(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    request = Request(NCBI_GENE_ORTHOLOG_URL, headers={"User-Agent": "IsoAPA/1.0"})
    try:
        with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        with gzip.open(temporary, "rt") as handle:
            header = handle.readline().strip()
        if header != "#tax_id\tGeneID\trelationship\tOther_tax_id\tOther_GeneID":
            raise ValueError("Unexpected NCBI gene_orthologs header")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_ortholog_source(
    source_path: str | Path | None = None,
    refresh: bool = False,
) -> Path:
    configured = source_path or os.environ.get("ISOAPA_GENE_ORTHOLOGS_FILE")
    source = Path(configured).expanduser() if configured else default_ortholog_cache_path()
    if refresh and not configured:
        source.unlink(missing_ok=True)
    if not source.is_file():
        if configured:
            raise FileNotFoundError(f"Ortholog source not found: {source}")
        _download_ortholog_source(source)
    return source


def rebuild_ortholog_relations(
    db: Session,
    source_path: str | Path | None = None,
    refresh: bool = False,
    batch_size: int = 10_000,
    species_ids: list[int] | None = None,
) -> dict:
    """Replace the ortholog index with relations present in the IsoAPA gene set."""
    source = resolve_ortholog_source(source_path, refresh=refresh)
    updated_species = ensure_species_taxids(db, species_ids)
    selected_species = set(species_ids) if species_ids is not None else None

    gene_lookup: dict[tuple[int, str], tuple[int, int]] = {}
    rows = (
        db.query(Gene.id, Gene.species_id, Gene.gene_id, Species.tax_id)
        .join(Species, Gene.species_id == Species.id)
        .filter(Species.tax_id.isnot(None))
        .all()
    )
    for gene_db_id, species_id, gene_id, tax_id in rows:
        external_id = str(gene_id or "").strip()
        if external_id.isdigit():
            gene_lookup[(int(tax_id), external_id)] = (gene_db_id, species_id)

    pairs: set[tuple[int, int]] = set()
    scanned = 0
    with gzip.open(source, "rt") as handle:
        header = handle.readline().strip()
        if header != "#tax_id\tGeneID\trelationship\tOther_tax_id\tOther_GeneID":
            raise ValueError("Unexpected NCBI gene_orthologs header")
        for line in handle:
            scanned += 1
            tax_id, gene_id, _relationship, other_tax_id, other_gene_id = line.rstrip(
                "\n"
            ).split("\t")
            first = gene_lookup.get((int(tax_id), gene_id))
            second = gene_lookup.get((int(other_tax_id), other_gene_id))
            if not first or not second or first[1] == second[1]:
                continue
            if selected_species is not None and not ({first[1], second[1]} & selected_species):
                continue
            pairs.add(tuple(sorted((first[0], second[0]))))

    relations = db.query(OrthologRelation)
    if species_ids is not None:
        affected_genes = db.query(Gene.id).filter(Gene.species_id.in_(species_ids))
        relations = relations.filter(or_(
            OrthologRelation.gene_a_id.in_(affected_genes),
            OrthologRelation.gene_b_id.in_(affected_genes),
        ))
    relations.delete(synchronize_session=False)
    ordered_pairs = sorted(pairs)
    for start in range(0, len(ordered_pairs), batch_size):
        db.bulk_insert_mappings(
            OrthologRelation,
            [
                {
                    "gene_a_id": gene_a_id,
                    "gene_b_id": gene_b_id,
                    "relationship": "Ortholog",
                    "source": ORTHOLOG_SOURCE_NAME,
                }
                for gene_a_id, gene_b_id in ordered_pairs[start : start + batch_size]
            ],
        )
        db.flush()
    db.commit()

    mapped_genes = {gene_id for pair in pairs for gene_id in pair}
    return {
        "source": str(source),
        "source_name": ORTHOLOG_SOURCE_NAME,
        "source_rows_scanned": scanned,
        "species_taxids_updated": updated_species,
        "eligible_genes": len(gene_lookup),
        "relation_count": len(pairs),
        "mapped_gene_count": len(mapped_genes),
    }
