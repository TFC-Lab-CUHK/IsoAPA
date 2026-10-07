import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
from app.models.database import (
    SessionLocal,
    Species,
    Sample,
    Gene,
    Transcript,
    APASite,
    APASiteSample,
    init_db,
)
from app.services.search_index import rebuild_search_index
from app.services.orthologs import taxonomy_record_for_species
from app.services.pas_evidence_stats import annotation_motif_model

SPECIES_MAP = {
    "homo_sapiens": {
        "name": "Human",
        "latin_name": "Homo sapiens",
        "assembly": "GRCh38",
    },
    "Homo_sapiens": {
        "name": "Human",
        "latin_name": "Homo sapiens",
        "assembly": "GRCh38",
    },
    "mus_musculus": {
        "name": "Mouse",
        "latin_name": "Mus musculus",
        "assembly": "GRCm39",
    },
    "Mus_musculus": {
        "name": "Mouse",
        "latin_name": "Mus musculus",
        "assembly": "GRCm39",
    },
    "rattus_norvegicus": {
        "name": "Rat",
        "latin_name": "Rattus norvegicus",
        "assembly": "rn6",
    },
    "danio_rerio": {
        "name": "Zebrafish",
        "latin_name": "Danio rerio",
        "assembly": "GRCz11",
    },
}

DATA_DIR = None

BATCH_SIZE = 5000


def _is_backup_name(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("backup", ".bak", "_bak", "old"))


def _cell(row: dict, *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return default


def _int_cell(row: dict, *names: str, default: int = 0) -> int:
    value = _cell(row, *names)
    if value == "":
        return default
    return int(float(value))


def _float_cell(row: dict, *names: str, default: float = 0.0) -> float:
    value = _cell(row, *names)
    if value == "":
        return default
    return float(value)


def _gene_key(row: dict) -> str:
    gene_id = _cell(row, "gene_id")
    if gene_id:
        return gene_id
    return "|".join(
        [
            _cell(row, "gene_name", default="unknown"),
            _cell(row, "chromosome", default="unknown"),
            _cell(row, "strand", default="unknown"),
        ]
    )


def _unified_file_path(species_folder: str) -> str | None:
    species_dir = os.path.join(DATA_DIR, species_folder)
    for fname in sorted(os.listdir(species_dir)):
        if _is_backup_name(fname):
            continue
        if fname.endswith("_unified_apa_sites.txt") or fname.endswith(
            "_unified_apa_sites.tsv"
        ):
            return os.path.join(species_dir, fname)
    return None


def _get_or_create_species(db, species_folder: str):
    info = SPECIES_MAP.get(
        species_folder,
        {
            "name": species_folder,
            "latin_name": species_folder,
            "assembly": None,
        },
    )
    taxonomy = taxonomy_record_for_species(
        species_folder,
        info.get("latin_name"),
    )
    obj = db.query(Species).filter(Species.name == info["name"]).first()
    if not obj:
        obj = Species(
            name=info["name"],
            latin_name=info["latin_name"],
            assembly=info.get("assembly"),
            tax_id=taxonomy.get("tax_id") if taxonomy else None,
        )
        db.add(obj)
        db.flush()
    elif taxonomy and obj.tax_id != taxonomy.get("tax_id"):
        obj.tax_id = taxonomy.get("tax_id")
    return obj


def _anno_file_path(species_path: str) -> str | None:
    for fname in sorted(os.listdir(species_path)):
        if _is_backup_name(fname):
            continue
        if fname.endswith("_unified_apa.anno.txt"):
            return os.path.join(species_path, fname)
    return None


def _load_anno_index(species_path: str, species_folder: str) -> dict:
    ann_path = _anno_file_path(species_path)
    if not ann_path:
        print(
            f"  No .anno.txt file found for {species_folder} — annotation columns will be NULL"
        )
        return {}
    print(f"  Loading annotation index: {os.path.basename(ann_path)}")
    index: dict = {}
    with open(ann_path) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            uid = _cell(row, "cluster_key", "unified_ID")
            pas_pos = row.get("pas_position", "").strip()
            c_start = row.get("cluster_start", "").strip()
            c_end = row.get("cluster_end", "").strip()
            index[uid] = {
                "sequence": row.get("sequence", "").strip() or None,
                "pas_motif": row.get("pas_motif", "").strip() or None,
                "pas_position": int(pas_pos) if pas_pos else None,
                "pas_type": row.get("pas_type", "").strip() or None,
                "search_level": row.get("search_level", "").strip() or None,
                "pa_level": row.get("pa_level", "").strip() or None,
                "motif_model": row.get("motif_model", "").strip() or None,
                "cluster_start": int(c_start) if c_start else None,
                "cluster_end": int(c_end) if c_end else None,
            }
    print(f"  Annotation index: {len(index):,} entries")
    return index


def ingest_data(data_dir: str = None, species_filter: list[str] | None = None):
    global DATA_DIR
    DATA_DIR = data_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data",
    )

    db = SessionLocal()
    try:
        print("Initializing database...")
        init_db()

        total_species = total_samples = total_genes = total_transcripts = (
            total_apa_sites
        ) = 0

        wanted_species = set(species_filter or [])
        processed_species_ids = []

        for species_folder in sorted(os.listdir(DATA_DIR)):
            species_path = os.path.join(DATA_DIR, species_folder)
            if not os.path.isdir(species_path) or species_folder.startswith("."):
                continue
            if wanted_species and species_folder not in wanted_species:
                continue

            unified_path = _unified_file_path(species_folder)
            if not unified_path:
                print(f"  Skipping {species_folder}: no unified APA sites file found")
                continue

            print(f"\nProcessing species: {species_folder}")
            print(f"  File: {os.path.basename(unified_path)}")

            species_obj = _get_or_create_species(db, species_folder)
            species_id = species_obj.id
            processed_species_ids.append(species_id)
            total_species += 1

            clusters: dict = {}
            sample_map: dict[str, str] = {}

            print("  Pass 1: reading file and aggregating clusters...")
            row_count = 0
            with open(unified_path, "r") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for row in reader:
                    row_count += 1
                    if row_count % 500_000 == 0:
                        print(f"    ... {row_count:,} rows read")

                    transcript_id = _cell(row, "transcript_id")
                    unified_id = _cell(row, "cluster_key", "unified_ID")
                    cluster_key = (transcript_id, unified_id)

                    entry = {
                        "sample_name": _cell(row, "sample"),
                        "sample_type": _cell(row, "sample_attribute"),
                        "original_site_position": _int_cell(row, "original_site_position"),
                        "site_count": _int_cell(row, "site_count"),
                        "site_abundance": _float_cell(
                            row, "cluster_relative_abundance", "site_abundance"
                        ),
                    }

                    if cluster_key not in clusters:
                        clusters[cluster_key] = {
                            "row": row,
                            "sample_entries": [entry],
                        }
                    else:
                        clusters[cluster_key]["sample_entries"].append(entry)

                    sample_map[entry["sample_name"]] = entry["sample_type"]

            print(
                f"  Rows: {row_count:,} | Clusters: {len(clusters):,} | "
                f"Samples: {len(sample_map)}"
            )

            print("  Pass 2: inserting samples...")
            sample_id_cache: dict[str, int] = {}
            for sname, stype in sample_map.items():
                obj = (
                    db.query(Sample)
                    .filter(Sample.name == sname, Sample.species_id == species_id)
                    .first()
                )
                if not obj:
                    obj = Sample(name=sname, sample_type=stype, species_id=species_id)
                    db.add(obj)
                    db.flush()
                sample_id_cache[sname] = obj.id
            db.commit()
            total_samples += len(sample_id_cache)

            print("  Pass 3: inserting genes and transcripts...")
            gene_id_cache: dict[str, int] = {}
            transcript_id_cache: dict[str, int] = {}

            for (transcript_id_str, unified_id), cluster in clusters.items():
                row = cluster["row"]
                gene_id_str = _cell(row, "gene_id")
                gene_key = _gene_key(row)

                if gene_key not in gene_id_cache:
                    obj = (
                        db.query(Gene)
                        .filter(
                            Gene.gene_key == gene_key,
                            Gene.species_id == species_id,
                        )
                        .first()
                    )
                    if not obj:
                        obj = Gene(
                            gene_id=gene_id_str,
                            gene_key=gene_key,
                            gene_name=_cell(row, "gene_name"),
                            chromosome=_cell(row, "chromosome"),
                            strand=_cell(row, "strand"),
                            species_id=species_id,
                        )
                        db.add(obj)
                        db.flush()
                    gene_id_cache[gene_key] = obj.id

                gene_db_id = gene_id_cache[gene_key]

                if transcript_id_str not in transcript_id_cache:
                    obj = (
                        db.query(Transcript)
                        .filter(
                            Transcript.transcript_id == transcript_id_str,
                            Transcript.species_id == species_id,
                        )
                        .first()
                    )
                    if not obj:
                        obj = Transcript(
                            transcript_id=transcript_id_str,
                            gene_id=gene_db_id,
                            species_id=species_id,
                        )
                        db.add(obj)
                        db.flush()
                    transcript_id_cache[transcript_id_str] = obj.id

            db.commit()
            total_genes += len(gene_id_cache)
            total_transcripts += len(transcript_id_cache)
            print(
                f"  Genes: {len(gene_id_cache):,} | Transcripts: {len(transcript_id_cache):,}"
            )

            print("  Pass 4: inserting APA sites in batches...")
            anno_index = _load_anno_index(species_path, species_folder)
            species_obj.motif_model = annotation_motif_model(
                ann["motif_model"] for ann in anno_index.values()
            )
            db.flush()
            batch = []
            sample_batch = []
            inserted = 0
            sample_rows = 0

            def flush_apa_batch():
                nonlocal batch, sample_batch, inserted, sample_rows
                if not batch:
                    return
                insert_rows = [
                    {k: v for k, v in site_row.items() if k != "_sample_entries"}
                    for site_row in batch
                ]
                start_id = db.query(APASite.id).order_by(APASite.id.desc()).limit(1).scalar() or 0
                db.bulk_insert_mappings(APASite, insert_rows)
                db.commit()
                inserted += len(batch)

                id_rows = (
                    db.query(APASite.id, APASite.transcript_id, APASite.unified_id)
                    .filter(
                        APASite.species_id == species_id,
                        APASite.id > start_id,
                    )
                    .all()
                )
                site_id_map = {
                    (transcript_id, unified_id): site_id
                    for site_id, transcript_id, unified_id in id_rows
                }

                sample_batch = []
                for site_row, insert_row in zip(batch, insert_rows):
                    apa_site_id = site_id_map.get(
                        (insert_row["transcript_id"], insert_row["unified_id"])
                    )
                    if not apa_site_id:
                        continue
                    for sample_order, entry in enumerate(site_row.pop("_sample_entries")):
                        sample_id = sample_id_cache.get(entry["sample_name"])
                        if not sample_id:
                            continue
                        sample_batch.append(
                            {
                                "apa_site_id": apa_site_id,
                                "sample_id": sample_id,
                                "sample_order": sample_order,
                                "original_site_position": entry["original_site_position"],
                                "site_count": entry["site_count"],
                                "site_abundance": entry["site_abundance"],
                            }
                        )
                if sample_batch:
                    db.bulk_insert_mappings(APASiteSample, sample_batch)
                    db.commit()
                    sample_rows += len(sample_batch)

                batch = []
                sample_batch = []

            for (transcript_id_str, unified_id), cluster in clusters.items():
                row = cluster["row"]
                sample_entries = cluster["sample_entries"]
                transcript_db_id = transcript_id_cache[transcript_id_str]

                total_count = sum(e["site_count"] for e in sample_entries)
                mean_abundance = (
                    sum(e["site_abundance"] for e in sample_entries)
                    / len(sample_entries)
                    if sample_entries
                    else 0.0
                )

                ann = anno_index.get(unified_id, {})
                batch.append(
                    {
                        "unified_id": unified_id,
                        "transcript_id": transcript_db_id,
                        "species_id": species_id,
                        "mode_site_position": _int_cell(row, "mode_site_position"),
                        "transcript_biotype": _cell(row, "transcript_biotype") or None,
                        "representative_status": _cell(
                            row,
                            "representative_status",
                            default="not_representative",
                        )
                        or "not_representative",
                        "site_count": total_count,
                        "site_abundance": mean_abundance,
                        "sample_data": None,
                        "sequence": ann.get("sequence"),
                        "pas_motif": ann.get("pas_motif"),
                        "pas_position": ann.get("pas_position"),
                        "pas_type": ann.get("pas_type"),
                        "search_level": ann.get("search_level"),
                        "pa_level": ann.get("pa_level"),
                        "cluster_start": ann.get("cluster_start"),
                        "cluster_end": ann.get("cluster_end"),
                        "_sample_entries": sample_entries,
                    }
                )

                if len(batch) >= BATCH_SIZE:
                    flush_apa_batch()
                    print(f"    ... {inserted:,} APA sites inserted")

            flush_apa_batch()

            total_apa_sites += inserted
            print(f"  APA sites inserted: {inserted:,}")
            print(f"  Sample observations inserted: {sample_rows:,}")

        print(f"\n=== Summary ===")
        print(f"Species:     {total_species}")
        print(f"Samples:     {total_samples}")
        print(f"Genes:       {total_genes}")
        print(f"Transcripts: {total_transcripts}")
        print(f"APA Sites:   {total_apa_sites}")
        print("Building search index...")
        rebuild_search_index(db, species_ids=processed_species_ids if wanted_species else None)
        print("Done.")

    except Exception:
        db.rollback()
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    default_data_dir = os.path.join(project_root, "data")

    parser = argparse.ArgumentParser(
        description="Ingest APA sites data (unified format)"
    )
    parser.add_argument("--data-dir", default=default_data_dir, help="Data directory")
    parser.add_argument(
        "--species",
        action="append",
        dest="species_filter",
        help="Species folder to ingest. Repeat for multiple species.",
    )
    args = parser.parse_args()

    ingest_data(args.data_dir, args.species_filter)
