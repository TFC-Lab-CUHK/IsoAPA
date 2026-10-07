from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from typing import List, Optional
import os
import json
import csv
import io
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from app.models.database import (
    get_db,
    Gene,
    Transcript,
    APASite,
    Species,
    Sample,
    APASiteSample,
    OrthologRelation,
    TranscriptSearchIndex,
    TranscriptSearchSample,
)
from app.services.search_index import ensure_search_index
from app.services.precompute_stats import STATS_CACHE_FILE, build_stats_cache
from app.services.pas_motif_stats import PRIMARY_PAS_TYPES, summarize_pas_motif_rows
from app.services.pas_evidence_stats import build_pas_evidence_summary
from app.services.ortholog_usage import pooled_gene_samples
from app.services.species_aliases import species_aliases, species_match_rank
from app.schemas.schemas import (
    SearchResult,
    SearchResponse,
    DashboardStats,
    LocusDetail,
    APASiteWithDetails,
    GeneDetail,
)

router = APIRouter()

_BED12_INDEX_CACHE: dict = {}
_TAXID_CACHE: dict = {}
_GENE_SUMMARY_CACHE: dict = {}
_STATS_CACHE: dict | None = None

_KNOWN_SPECIES_TAXIDS = {
    "Human": "9606",
    "Homo sapiens": "9606",
    "Homo_sapiens": "9606",
    "Mouse": "10090",
    "Mus musculus": "10090",
    "Mus_musculus": "10090",
    "Rat": "10116",
    "Rattus norvegicus": "10116",
    "Rattus_norvegicus": "10116",
    "Zebrafish": "7955",
    "Danio rerio": "7955",
    "Danio_rerio": "7955",
}


def _format_sample_name(name: str) -> str:
    return " ".join(str(name or "").replace("_", " ").split())


def _download_filename(name: str) -> str:
    """Keep Content-Disposition filenames ASCII-safe and header-safe."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or "").strip())
    return safe.strip("._") or "download"


def _sample_display_key(name: str) -> str:
    return _format_sample_name(name).lower()


def _dedupe_sample_names(names) -> list[str]:
    seen = set()
    deduped = []
    for name in names:
        key = _sample_display_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(name)
    return deduped


def _dedupe_sample_details(details: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for detail in details or []:
        key = _sample_display_key(detail.get("sample_name", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(detail)
    return deduped


def _format_species_name(name: str, latin_name: Optional[str] = None) -> str:
    formal_names = {
        "Human": "Homo sapiens",
        "Mouse": "Mus musculus",
    }
    if name in formal_names:
        return formal_names[name]

    preferred = latin_name if latin_name and latin_name != name else name
    return str(preferred or "").replace("_", " ")


def _ranked_species_matches(db: Session, query: str):
    matches = []
    for species_name, latin_name in db.query(Species.name, Species.latin_name).all():
        rank = species_match_rank(query, species_name, latin_name)
        if rank is None:
            continue
        matches.append((rank, _format_species_name(species_name, latin_name).casefold(), species_name, latin_name))
    return sorted(matches)


def _matching_species_names(db: Session, query: str) -> list[str]:
    matches = _ranked_species_matches(db, query)
    if not matches:
        return []
    best_rank = matches[0][0]
    return [species_name for rank, _, species_name, _ in matches if rank == best_rank]


def _ortholog_neighbor_ids(db: Session, gene_db_id: int) -> list[int]:
    rows = (
        db.query(OrthologRelation.gene_a_id, OrthologRelation.gene_b_id)
        .filter(
            or_(
                OrthologRelation.gene_a_id == gene_db_id,
                OrthologRelation.gene_b_id == gene_db_id,
            )
        )
        .all()
    )
    return sorted(
        {
            gene_b_id if gene_a_id == gene_db_id else gene_a_id
            for gene_a_id, gene_b_id in rows
        }
    )


def _gene_comparison_summaries(db: Session, gene_ids: list[int]) -> list[dict]:
    requested = list(dict.fromkeys(gene_ids))
    if not requested:
        return []

    gene_rows = (
        db.query(Gene, Species)
        .join(Species, Gene.species_id == Species.id)
        .filter(Gene.id.in_(requested))
        .all()
    )
    transcript_rows = (
        db.query(Transcript.id, Transcript.gene_id)
        .filter(Transcript.gene_id.in_(requested))
        .all()
    )
    transcript_ids = [row[0] for row in transcript_rows]
    transcript_gene = {transcript_id: gene_id for transcript_id, gene_id in transcript_rows}
    site_counts_by_transcript: dict[int, int] = {}
    unique_sites_by_gene: dict[int, set[str]] = {gene_id: set() for gene_id in requested}
    if transcript_ids:
        site_rows = (
            db.query(APASite.transcript_id, APASite.unified_id)
            .filter(APASite.transcript_id.in_(transcript_ids))
            .all()
        )
        transcript_sites: dict[int, set[str]] = {}
        for transcript_id, unified_id in site_rows:
            transcript_sites.setdefault(transcript_id, set()).add(unified_id)
            gene_id = transcript_gene.get(transcript_id)
            if gene_id is not None:
                unique_sites_by_gene.setdefault(gene_id, set()).add(unified_id)
        site_counts_by_transcript = {
            transcript_id: len(site_ids)
            for transcript_id, site_ids in transcript_sites.items()
        }

    sample_counts = dict(
        db.query(Transcript.gene_id, func.count(func.distinct(APASiteSample.sample_id)))
        .join(APASite, APASite.transcript_id == Transcript.id)
        .join(APASiteSample, APASiteSample.apa_site_id == APASite.id)
        .filter(Transcript.gene_id.in_(requested))
        .group_by(Transcript.gene_id)
        .all()
    )
    transcripts_by_gene: dict[int, list[int]] = {gene_id: [] for gene_id in requested}
    for transcript_id, gene_id in transcript_rows:
        transcripts_by_gene.setdefault(gene_id, []).append(transcript_id)

    summaries = []
    for gene, species in gene_rows:
        gene_transcripts = transcripts_by_gene.get(gene.id, [])
        linked_site_count = sum(
            site_counts_by_transcript.get(transcript_id, 0)
            for transcript_id in gene_transcripts
        )
        multi_pas_count = sum(
            site_counts_by_transcript.get(transcript_id, 0) >= 2
            for transcript_id in gene_transcripts
        )
        transcript_count = len(gene_transcripts)
        summaries.append(
            {
                "gene_db_id": gene.id,
                "gene_id": gene.gene_id,
                "gene_name": gene.gene_name,
                "chromosome": gene.chromosome,
                "strand": gene.strand,
                "species": species.name,
                "scientific_name": _format_species_name(species.name, species.latin_name),
                "tax_id": species.tax_id,
                "transcript_count": transcript_count,
                "pa_site_count": len(unique_sites_by_gene.get(gene.id, set())),
                "transcript_pa_link_count": linked_site_count,
                "mean_pa_sites_per_transcript": round(
                    linked_site_count / transcript_count, 2
                )
                if transcript_count
                else 0,
                "multi_pas_transcript_count": multi_pas_count,
                "multi_pas_transcript_pct": round(
                    100 * multi_pas_count / transcript_count, 1
                )
                if transcript_count
                else 0,
                "sample_count": int(sample_counts.get(gene.id, 0)),
            }
        )
    summary_by_id = {row["gene_db_id"]: row for row in summaries}
    return [summary_by_id[gene_id] for gene_id in requested if gene_id in summary_by_id]


def _load_stats_cache() -> dict:
    global _STATS_CACHE
    if _STATS_CACHE is not None:
        return _STATS_CACHE
    if os.path.exists(STATS_CACHE_FILE):
        with open(STATS_CACHE_FILE) as fh:
            _STATS_CACHE = json.load(fh)
    else:
        _STATS_CACHE = build_stats_cache(STATS_CACHE_FILE)
    return _STATS_CACHE


def _chunks(values: list[int], size: int = 800):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _sample_detail_rows(db: Session, apa_site_ids: list[int]) -> dict[int, list[dict]]:
    site_ids = [site_id for site_id in apa_site_ids if site_id]
    if not site_ids:
        return {}

    grouped: dict[int, list[dict]] = {site_id: [] for site_id in site_ids}
    for site_id_chunk in _chunks(site_ids):
        rows = (
            db.query(
                APASiteSample.apa_site_id,
                Sample.name,
                Sample.sample_type,
                APASiteSample.sample_order,
                APASiteSample.original_site_position,
                APASiteSample.site_count,
                APASiteSample.site_abundance,
            )
            .join(Sample, APASiteSample.sample_id == Sample.id)
            .filter(APASiteSample.apa_site_id.in_(site_id_chunk))
            .order_by(APASiteSample.apa_site_id, APASiteSample.sample_order)
            .all()
        )
        for site_id, sample_name, sample_type, _sample_order, position, count, abundance in rows:
            grouped.setdefault(site_id, []).append(
                {
                    "sample_name": sample_name,
                    "sample_type": sample_type,
                    "original_site_position": position,
                    "site_count": count,
                    "site_abundance": abundance,
                }
            )
    return grouped


def _sample_site_filter(db: Session, sample_names: list[str]):
    names = [sample_name for sample_name in sample_names if sample_name]
    if not names:
        return None
    normalized_sites = (
        db.query(APASiteSample.apa_site_id)
        .join(Sample, APASiteSample.sample_id == Sample.id)
        .filter(Sample.name.in_(names) if len(names) > 1 else Sample.name.ilike(f"%{names[0]}%"))
    )
    return APASite.id.in_(normalized_sites)


def _search_terms(value: Optional[str]) -> tuple[str, str]:
    raw = str(value or "").strip()
    normalized = raw.replace(" ", "_")
    return raw, normalized.lower()


def _like_term(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def _prefix_upper_bound(term: str) -> str:
    if not term:
        return term
    return f"{term[:-1]}{chr(ord(term[-1]) + 1)}"


def _write_apa_site_download_row(writer, row, sample_detail: dict | None, delimiter_selected_samples: list[str]):
    cluster_range = (
        f"{row.cluster_start}:{row.cluster_end}"
        if row.cluster_start is not None and row.cluster_end is not None
        else ""
    )
    sample_name = (sample_detail or {}).get("sample_name", "")
    if delimiter_selected_samples and sample_name not in delimiter_selected_samples:
        return
    writer.writerow(
        {
            "gene_name": row.gene_name or "",
            "gene_id": row.gene_id or "",
            "transcript_id": row.transcript_id or "",
            "site_id": row.unified_id or "",
            "cluster_range": cluster_range,
            "representative_position": row.mode_site_position or "",
            "sample_site_position": (sample_detail or {}).get("original_site_position", ""),
            "site_abundance": (sample_detail or {}).get("site_abundance", ""),
            "species": _format_species_name(row.species),
            "sample": _format_sample_name(sample_name),
        }
    )


def _multiplicity_bucket(count: int) -> str:
    if count >= 5:
        return "5+"
    return str(count)


def _build_multiplicity_stats(db: Session, species: Optional[str] = None) -> dict:
    query = (
        db.query(Transcript.id, func.count(func.distinct(APASite.unified_id)).label("apa_count"))
        .outerjoin(APASite, APASite.transcript_id == Transcript.id)
        .join(Species, Transcript.species_id == Species.id)
    )
    if species:
        query = query.filter(Species.name == species)

    rows = query.group_by(Transcript.id).all()
    buckets = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
    single_count = 0
    multi_count = 0
    for _, count in rows:
        count = int(count or 0)
        buckets[_multiplicity_bucket(count)] += 1
        if count == 1:
            single_count += 1
        if count >= 2:
            multi_count += 1

    total = len(rows)
    return {
        "buckets": buckets,
        "total": total,
        "single_count": single_count,
        "multi_count": multi_count,
        "pct_single_site": round((single_count / total) * 100, 1) if total else 0,
        "pct_multi_site": round((multi_count / total) * 100, 1) if total else 0,
    }


def _build_top_gene_stats(db: Session, species: Optional[str] = None, *, limit: int = 10) -> list[dict]:
    distinct_site_count = func.count(func.distinct(APASite.unified_id))
    query = (
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
    )
    if species:
        query = query.filter(Species.name == species)

    rows = (
        query.group_by(Gene.gene_name, Gene.gene_id, Species.name, Gene.id)
        .order_by(distinct_site_count.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "gene_name": gene_name,
            "gene_id": gene_id,
            "species": species_name,
            "apa_count": apa_count,
            "gene_db_id": gene_db_id,
        }
        for gene_name, gene_id, species_name, apa_count, gene_db_id in rows
    ]


def _build_pas_motif_stats(db: Session, species: Optional[str] = None) -> dict:
    motif_rank = case(
        (APASite.pas_type.in_(PRIMARY_PAS_TYPES), 1),
        (APASite.pas_type == "not_assessed", 4),
        (APASite.pas_motif.is_(None), 3),
        (APASite.pas_motif == "", 3),
        else_=2,
    )
    site_choice = (
        db.query(
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
        )
        .join(Species, APASite.species_id == Species.id)
    )
    if species:
        site_choice = site_choice.filter(Species.name == species)

    deduped_sites = site_choice.subquery()
    query = (
        db.query(
            deduped_sites.c.motif,
            deduped_sites.c.motif_type,
            func.count(deduped_sites.c.site_id).label("site_count"),
        )
        .filter(deduped_sites.c.rn == 1)
        .group_by(deduped_sites.c.motif, deduped_sites.c.motif_type)
    )

    return summarize_pas_motif_rows(query.all())


def _cached_pas_motif_stats(species: Optional[str] = None) -> Optional[dict]:
    motif_cache = _load_stats_cache().get("detailed", {}).get("pas_motif_distribution")
    if not motif_cache:
        return None
    if species:
        return motif_cache.get("by_species", {}).get(species)
    return motif_cache.get("all")


def _http_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "IsoAPA/1.0"})
    with urlopen(req, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_species_taxid(species_name: str, latin_name: Optional[str] = None) -> str | None:
    candidates = [
        species_name,
        latin_name,
        _format_species_name(species_name, latin_name),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in _KNOWN_SPECIES_TAXIDS:
            return _KNOWN_SPECIES_TAXIDS[candidate]

    scientific_name = _format_species_name(species_name, latin_name)
    if not scientific_name:
        return None
    if scientific_name in _TAXID_CACHE:
        return _TAXID_CACHE[scientific_name]

    params = urlencode(
        {
            "db": "taxonomy",
            "term": f"{scientific_name}[Scientific Name]",
            "retmode": "json",
            "retmax": "1",
        }
    )
    try:
        data = _http_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}")
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    idlist = data.get("esearchresult", {}).get("idlist", [])
    taxid = idlist[0] if idlist else None
    _TAXID_CACHE[scientific_name] = taxid
    return taxid


def _first_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _query_transcript_by_public_id(
    db: Session, transcript_id: str, species: Optional[str] = None
):
    query = db.query(Transcript).filter(Transcript.transcript_id == transcript_id)
    if species:
        query = query.join(Species, Transcript.species_id == Species.id).filter(
            Species.name == species
        )
    return query.first()


def _load_bed12_index(bed12_path: str) -> dict:
    if bed12_path in _BED12_INDEX_CACHE:
        return _BED12_INDEX_CACHE[bed12_path]
    idx_path = bed12_path + ".bidx"
    if not os.path.exists(idx_path):
        return {}
    with open(idx_path, "r") as f:
        idx = json.load(f)
    _BED12_INDEX_CACHE[bed12_path] = idx
    return idx


def _fetch_bed12_record(bed12_path: str, transcript_id: str) -> dict | None:
    idx = _load_bed12_index(bed12_path)
    span = idx.get(transcript_id)
    if not span:
        return None
    offset, length = span
    with open(bed12_path, "rb") as f:
        f.seek(offset)
        line = f.read(length).decode("utf-8", errors="replace").strip()
    fields = line.split("\t")
    if len(fields) < 12:
        return None
    chrom_start = int(fields[1])
    thick_start = int(fields[6])
    thick_end = int(fields[7])
    block_sizes = [int(x) for x in fields[10].rstrip(",").split(",") if x]
    block_starts = [int(x) for x in fields[11].rstrip(",").split(",") if x]
    return {
        "chrom": fields[0],
        "chrom_start": chrom_start,
        "strand": fields[5],
        "thick_start": thick_start,
        "thick_end": thick_end,
        "block_sizes": block_sizes,
        "block_starts": block_starts,
    }


def _parse_bed12_structure(rec: dict) -> dict:
    cs = rec["chrom_start"]
    ts, te = rec["thick_start"], rec["thick_end"]
    has_cds = ts < te
    exons, cds, utrs = [], [], []

    for bstart_rel, bsize in zip(rec["block_starts"], rec["block_sizes"]):
        b_start = cs + bstart_rel
        b_end = b_start + bsize
        ex_s, ex_e = b_start + 1, b_end

        exons.append((ex_s, ex_e))

        if not has_cds:
            utrs.append((ex_s, ex_e))
            continue

        cds_s0 = max(b_start, ts)
        cds_e0 = min(b_end, te)

        if cds_s0 < cds_e0:
            cds.append((cds_s0 + 1, cds_e0))
            if b_start < ts:
                utrs.append((ex_s, ts))
            if b_end > te:
                utrs.append((te + 1, ex_e))
        else:
            utrs.append((ex_s, ex_e))

    return {
        "chrom": rec["chrom"],
        "strand": rec["strand"],
        "exons": exons,
        "cds": cds,
        "utrs": utrs,
    }


DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data"
)

SPECIES_FOLDER_MAP = {
    "Human": "Homo_sapiens",
    "Mouse": "Mus_musculus",
    "Rat": "rattus_norvegicus",
    "Zebrafish": "danio_rerio",
}


def get_species_ref_path(species_name: str, file_type: str = "bed12") -> str:
    """Get reference file path for a species."""
    species_folder = SPECIES_FOLDER_MAP.get(species_name, species_name.replace(" ", "_"))

    species_dir = os.path.join(DATA_DIR, species_folder)
    if not os.path.exists(species_dir):
        return None

    for f in os.listdir(species_dir):
        if file_type == "fasta" and (
            f.endswith(".fa") or f.endswith(".fasta") or f.endswith(".fna")
        ):
            return os.path.join(species_dir, f)
        elif file_type == "bed12" and f.endswith(".bed") and not f.endswith(".bidx"):
            return os.path.join(species_dir, f)

    return None


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics from the precomputed cache."""
    return DashboardStats(**_load_stats_cache()["basic"])


@router.get("/search", response_model=SearchResponse)
def search_transcripts(
    gene_name: Optional[str] = None,
    transcript_id: Optional[str] = None,
    gene_id: Optional[str] = None,
    sample: Optional[str] = None,
    species: Optional[str] = None,
    chromosome: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search for transcripts with filters."""
    ensure_search_index(db)
    query = (
        db.query(
            TranscriptSearchIndex.transcript_id,
            TranscriptSearchIndex.gene_id,
            TranscriptSearchIndex.gene_name,
            TranscriptSearchIndex.chromosome,
            TranscriptSearchIndex.strand,
            TranscriptSearchIndex.apa_site_count,
            TranscriptSearchIndex.species,
            TranscriptSearchIndex.species_id,
            TranscriptSearchIndex.transcript_db_id,
            TranscriptSearchIndex.gene_db_id,
        )
        .select_from(TranscriptSearchIndex)
    )

    if gene_name:
        term = _like_term(gene_name)
        upper = _prefix_upper_bound(term)
        has_prefix_match = (
            db.query(TranscriptSearchIndex.id)
            .filter(
                TranscriptSearchIndex.gene_name_lc >= term,
                TranscriptSearchIndex.gene_name_lc < upper,
            )
            .limit(1)
            .first()
            is not None
        )
        query = (
            query.filter(
                TranscriptSearchIndex.gene_name_lc >= term,
                TranscriptSearchIndex.gene_name_lc < upper,
            )
            if has_prefix_match
            else (
                query.filter(TranscriptSearchIndex.gene_name.ilike(f"%{term}%"))
                if len(term) < 6
                else query.filter(TranscriptSearchIndex.gene_name_lc == term)
            )
        )
    if transcript_id:
        term = _like_term(transcript_id)
        query = query.filter(TranscriptSearchIndex.transcript_id.ilike(f"%{term}%"))
    if gene_id:
        term = _like_term(gene_id)
        query = query.filter(TranscriptSearchIndex.gene_id.ilike(f"%{term}%"))
    sample_terms = []
    sample_count_subquery = None
    if sample:
        raw_sample = str(sample or "").strip()
        sample_terms = {raw_sample}
        if "_" in raw_sample:
            sample_terms.add(raw_sample.replace("_", " "))
        if " " in raw_sample:
            sample_terms.add(raw_sample.replace(" ", "_"))
        sample_terms = [sample_term for sample_term in sample_terms if sample_term]
        normalized_sample_terms = [sample_term.lower() for sample_term in sample_terms]
        exact_sample_exists = (
            db.query(TranscriptSearchSample.id)
            .filter(TranscriptSearchSample.sample_name_lc.in_(normalized_sample_terms))
            .limit(1)
            .first()
            is not None
        )
        sample_filter = (
            TranscriptSearchSample.sample_name_lc.in_(normalized_sample_terms)
            if exact_sample_exists
            else or_(*[
                TranscriptSearchSample.sample_name.ilike(f"%{sample_term}%")
                for sample_term in sample_terms
            ])
        )
        sample_count_subquery = (
            db.query(
                TranscriptSearchSample.transcript_db_id.label("transcript_db_id"),
                func.sum(TranscriptSearchSample.apa_site_count).label("sample_apa_site_count"),
            )
            .filter(sample_filter)
            .group_by(TranscriptSearchSample.transcript_db_id)
            .subquery()
        )
        query = query.join(
            sample_count_subquery,
            TranscriptSearchIndex.transcript_db_id == sample_count_subquery.c.transcript_db_id,
        ).add_columns(sample_count_subquery.c.sample_apa_site_count)
    if species:
        matching_species = _matching_species_names(db, species)
        query = query.filter(TranscriptSearchIndex.species.in_(matching_species))
    if chromosome:
        query = query.filter(TranscriptSearchIndex.chromosome.ilike(f"%{chromosome}%"))

    sort_columns = {
        "gene_name": TranscriptSearchIndex.gene_name,
        "transcript_id": TranscriptSearchIndex.transcript_id,
        "chromosome": TranscriptSearchIndex.chromosome,
        "strand": TranscriptSearchIndex.strand,
        "apa_site_count": (
            sample_count_subquery.c.sample_apa_site_count
            if sample_count_subquery is not None
            else TranscriptSearchIndex.apa_site_count
        ),
        "species": TranscriptSearchIndex.species,
    }
    order_by = []
    if gene_name:
        gene_term = _like_term(gene_name)
        if gene_term:
            order_by.append(
                case(
                    (TranscriptSearchIndex.gene_name_lc == gene_term, 0),
                    (TranscriptSearchIndex.gene_name_lc.like(f"{gene_term}%"), 1),
                    else_=2,
                )
            )
    if transcript_id:
        transcript_term = _like_term(transcript_id)
        if transcript_term:
            order_by.append(
                case(
                    (func.lower(TranscriptSearchIndex.transcript_id) == transcript_term, 0),
                    (func.lower(TranscriptSearchIndex.transcript_id).like(f"{transcript_term}%"), 1),
                    else_=2,
                )
            )
    if sort_by in sort_columns:
        sort_expr = sort_columns[sort_by]
        order_by.append(sort_expr.desc() if sort_desc else sort_expr.asc())
    order_by.extend([
        TranscriptSearchIndex.gene_name.asc(),
        TranscriptSearchIndex.transcript_id.asc(),
        TranscriptSearchIndex.species.asc(),
    ])

    total_count = query.count()

    results = (
        query.order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    transcript_db_ids = [r[8] for r in results]
    sample_names_by_transcript = {transcript_db_id: set() for transcript_db_id in transcript_db_ids}
    if transcript_db_ids:
        sample_rows = (
            db.query(
                TranscriptSearchSample.transcript_db_id,
                TranscriptSearchSample.sample_name,
            )
            .filter(TranscriptSearchSample.transcript_db_id.in_(transcript_db_ids))
            .order_by(
                TranscriptSearchSample.transcript_db_id,
                TranscriptSearchSample.sample_name,
            )
            .all()
        )
        for transcript_db_id, sample_name in sample_rows:
            sample_names_by_transcript.setdefault(transcript_db_id, set()).add(sample_name)

    search_results = []
    for r in results:
        search_results.append(
            SearchResult(
                transcript_id=r[0],
                gene_id=r[1],
                gene_name=r[2],
                chromosome=r[3],
                strand=r[4],
                apa_site_count=(
                    r[10]
                    if sample_count_subquery is not None
                    else r[5]
                ),
                cell_lines=_dedupe_sample_names(
                    sorted(
                        sample_names_by_transcript.get(r[8], set()),
                        key=lambda value: _format_sample_name(value).lower(),
                    )
                ),
                species=r[6],
                gene_db_id=r[9],
            )
        )

    return SearchResponse(items=search_results, total=total_count)


@router.get("/orthologs/search")
def search_ortholog_genes(
    species: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    species_names = _matching_species_names(db, species)
    if not species_names:
        return []

    term = q.strip().casefold()
    connected_gene_ids = db.query(OrthologRelation.gene_a_id).union(
        db.query(OrthologRelation.gene_b_id)
    )
    match_priority = case(
        (func.lower(Gene.gene_name) == term, 0),
        (func.lower(Gene.gene_id) == term, 0),
        (func.lower(Gene.gene_name).like(f"{term}%"), 1),
        (func.lower(Gene.gene_id).like(f"{term}%"), 1),
        else_=2,
    )
    genes = (
        db.query(Gene, Species)
        .join(Species, Gene.species_id == Species.id)
        .filter(
            Species.name.in_(species_names),
            Gene.id.in_(connected_gene_ids),
            or_(
                Gene.gene_name.ilike(f"%{q.strip()}%"),
                Gene.gene_id.ilike(f"%{q.strip()}%"),
            ),
        )
        .order_by(match_priority, func.lower(Gene.gene_name), Gene.gene_id)
        .limit(limit)
        .all()
    )

    results = []
    for gene, species_row in genes:
        neighbor_ids = _ortholog_neighbor_ids(db, gene.id)
        ortholog_species_count = 0
        if neighbor_ids:
            ortholog_species_count = (
                db.query(func.count(func.distinct(Gene.species_id)))
                .filter(Gene.id.in_(neighbor_ids))
                .scalar()
                or 0
            )
        results.append(
            {
                "gene_db_id": gene.id,
                "gene_id": gene.gene_id,
                "gene_name": gene.gene_name,
                "species": species_row.name,
                "scientific_name": _format_species_name(
                    species_row.name, species_row.latin_name
                ),
                "ortholog_count": len(neighbor_ids),
                "ortholog_species_count": int(ortholog_species_count),
            }
        )
    return results


@router.get("/orthologs/compare")
def compare_ortholog_genes(
    gene_ids: str,
    max_transcripts: int = Query(12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    try:
        requested_gene_ids = list(
            dict.fromkeys(
                int(value.strip())
                for value in gene_ids.split(",")
                if value.strip()
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="gene_ids must be integers") from exc
    if not requested_gene_ids:
        raise HTTPException(status_code=400, detail="At least one gene is required")
    if len(requested_gene_ids) > 8:
        raise HTTPException(status_code=400, detail="At most eight genes can be compared")

    source_gene_id = requested_gene_ids[0]
    allowed_gene_ids = {source_gene_id, *_ortholog_neighbor_ids(db, source_gene_id)}
    if any(gene_id not in allowed_gene_ids for gene_id in requested_gene_ids[1:]):
        raise HTTPException(
            status_code=400,
            detail="All comparison genes must be direct orthologs of the first gene",
        )

    summaries = _gene_comparison_summaries(db, requested_gene_ids)
    if len(summaries) != len(requested_gene_ids):
        raise HTTPException(status_code=404, detail="One or more genes were not found")
    summary_by_id = {row["gene_db_id"]: row for row in summaries}

    transcript_rows = (
        db.query(Transcript.id, Transcript.transcript_id, Transcript.gene_id)
        .filter(Transcript.gene_id.in_(requested_gene_ids))
        .all()
    )
    transcript_gene = {row.id: row.gene_id for row in transcript_rows}
    transcript_public_id = {row.id: row.transcript_id for row in transcript_rows}
    transcript_ids = list(transcript_gene)
    site_rows = []
    if transcript_ids:
        site_rows = (
            db.query(
                APASite.id,
                APASite.transcript_id,
                APASite.unified_id,
                APASite.mode_site_position,
                APASite.cluster_start,
                APASite.cluster_end,
                APASite.pas_motif,
                APASite.pas_type,
                APASite.pa_level,
                APASite.transcript_biotype,
                APASite.representative_status,
            )
            .filter(APASite.transcript_id.in_(transcript_ids))
            .all()
        )

    sites_by_transcript: dict[int, list] = {}
    for row in site_rows:
        sites_by_transcript.setdefault(row.transcript_id, []).append(row)
    selected_transcript_ids: set[int] = set()
    for gene_id in requested_gene_ids:
        candidates = [row.id for row in transcript_rows if row.gene_id == gene_id]
        candidates.sort(
            key=lambda transcript_id: (
                -len(sites_by_transcript.get(transcript_id, [])),
                transcript_public_id[transcript_id],
            )
        )
        selected_transcript_ids.update(candidates[:max_transcripts])

    selected_site_ids = [
        row.id
        for transcript_id in selected_transcript_ids
        for row in sites_by_transcript.get(transcript_id, [])
    ]
    sample_details_by_site = _sample_detail_rows(db, selected_site_ids)
    sample_registry: dict[str, dict] = {}
    genes_payload: dict[int, dict] = {
        summary["gene_db_id"]: {**summary, "transcripts": []}
        for summary in summaries
    }

    # Gene tracks and denominators include every transcript, independently of
    # the display limit applied to the transcript tracks below.
    pooled_samples = pooled_gene_samples(db, requested_gene_ids)
    metadata_by_gene: dict[int, dict] = {gene_id: {} for gene_id in requested_gene_ids}
    for row in site_rows:
        gene_id = transcript_gene[row.transcript_id]
        metadata_by_gene[gene_id].setdefault(row.unified_id, {
            "site_id": row.unified_id,
            "position": row.mode_site_position,
            "cluster_start": row.cluster_start,
            "cluster_end": row.cluster_end,
            "pas_motif": row.pas_motif,
            "pas_type": row.pas_type,
            "pa_level": row.pa_level,
        })
    for gene_id, metadata in metadata_by_gene.items():
        summary = summary_by_id[gene_id]
        sites = sorted(metadata.values(), key=lambda site: (site["position"], site["site_id"]),
                       reverse=summary["strand"] == "-")
        for order, site in enumerate(sites, 1):
            samples = pooled_samples[gene_id].get(site["site_id"], [])
            site.update({
                "site_order": order,
                "samples": samples,
                "sample_count": len(samples),
                "mean_abundance": sum(s["abundance"] for s in samples) / len(samples) if samples else None,
            })
            for sample in samples:
                registry = sample_registry.setdefault(sample["key"], {
                    "value": sample["key"], "title": sample["name"], "species": set(),
                })
                registry["species"].add(summary["species"])
        genes_payload[gene_id]["sites"] = sites

    for transcript_id in sorted(
        selected_transcript_ids,
        key=lambda value: (transcript_gene[value], transcript_public_id[value]),
    ):
        gene_id = transcript_gene[transcript_id]
        summary = summary_by_id[gene_id]
        rows = sites_by_transcript.get(transcript_id, [])
        rows = sorted(
            rows,
            key=lambda row: row.mode_site_position,
            reverse=summary["strand"] == "-",
        )
        site_payload = []
        for row in rows:
            sample_details = _dedupe_sample_details(
                sample_details_by_site.get(row.id, [])
            )
            samples = []
            for detail in sample_details:
                display_name = _format_sample_name(detail.get("sample_name", ""))
                sample_key = _sample_display_key(display_name)
                if sample_key:
                    registry = sample_registry.setdefault(
                        sample_key,
                        {
                            "value": sample_key,
                            "title": display_name,
                            "species": set(),
                        },
                    )
                    registry["species"].add(summary["species"])
                samples.append(
                    {
                        "name": display_name,
                        "key": sample_key,
                        "sample_type": detail.get("sample_type"),
                        "site_count": detail.get("site_count", 0),
                        "abundance": detail.get("site_abundance", 0),
                    }
                )
            abundances = [
                float(sample["abundance"] or 0)
                for sample in samples
                if sample.get("abundance") is not None
            ]
            site_payload.append(
                {
                    "site_id": row.unified_id,
                    "position": row.mode_site_position,
                    "cluster_start": row.cluster_start,
                    "cluster_end": row.cluster_end,
                    "pas_motif": row.pas_motif,
                    "pas_type": row.pas_type,
                    "pa_level": row.pa_level,
                    "site_order": metadata_by_gene[gene_id][row.unified_id]["site_order"],
                    "mean_abundance": round(
                        sum(abundances) / len(abundances), 6
                    )
                    if abundances
                    else 0,
                    "sample_count": len(samples),
                    "samples": samples,
                }
            )
        genes_payload[gene_id]["transcripts"].append(
            {
                "transcript_id": transcript_public_id[transcript_id],
                "transcript_biotype": next(
                    (row.transcript_biotype for row in rows if row.transcript_biotype),
                    None,
                ),
                "representative_status": next(
                    (
                        row.representative_status
                        for row in rows
                        if row.representative_status
                        and row.representative_status != "not_representative"
                    ),
                    None,
                ),
                "sites": site_payload,
            }
        )

    sample_options = [
        {
            "value": record["value"],
            "title": record["title"],
            "species_count": len(record["species"]),
        }
        for record in sample_registry.values()
    ]
    sample_options.sort(key=lambda row: (-row["species_count"], row["title"].casefold()))
    return {
        "source": "NCBI Gene orthologs",
        "genes": [genes_payload[gene_id] for gene_id in requested_gene_ids],
        "sample_options": sample_options,
        "max_transcripts_per_gene": max_transcripts,
    }


@router.get("/orthologs/{gene_db_id}")
def get_gene_orthologs(gene_db_id: int, db: Session = Depends(get_db)):
    source_summary = _gene_comparison_summaries(db, [gene_db_id])
    if not source_summary:
        raise HTTPException(status_code=404, detail="Gene not found")
    neighbor_ids = _ortholog_neighbor_ids(db, gene_db_id)
    orthologs = _gene_comparison_summaries(db, neighbor_ids)
    orthologs.sort(
        key=lambda row: (
            row["scientific_name"].casefold(),
            row["gene_name"].casefold(),
            row["gene_id"],
        )
    )
    return {
        "source": "NCBI Gene orthologs",
        "source_gene": source_summary[0],
        "orthologs": orthologs,
        "ortholog_count": len(orthologs),
        "species_count": len({row["species"] for row in orthologs}),
    }


@router.get("/gene/{gene_db_id}", response_model=GeneDetail)
def get_gene_detail(
    gene_db_id: int,
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get detailed information about a gene and all its transcripts with APA sites."""
    gene_query = db.query(Gene).filter(Gene.id == gene_db_id)
    if species:
        gene_query = gene_query.join(Species, Gene.species_id == Species.id).filter(
            Species.name == species
        )
    gene = gene_query.first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    transcripts = db.query(Transcript).filter(Transcript.gene_id == gene.id).all()

    species_obj = db.query(Species).filter(Species.id == gene.species_id).first()
    species_name = species_obj.name if species_obj else species

    transcript_data = []
    for transcript in transcripts:
        apa_sites = (
            db.query(APASite).filter(APASite.transcript_id == transcript.id).all()
        )
        sample_details_by_site = _sample_detail_rows(db, [site.id for site in apa_sites])

        sample_names = set()
        transcript_apa_sites = []
        for asite in apa_sites:
            sample_details = _dedupe_sample_details(sample_details_by_site.get(asite.id, []))
            for sd in sample_details:
                sample_names.add(sd.get("sample_name", ""))

            transcript_apa_sites.append(
                {
                    "unified_id": asite.unified_id,
                    "mode_site_position": asite.mode_site_position,
                    "site_abundance": asite.site_abundance,
                    "site_count": asite.site_count,
                    "transcript_biotype": asite.transcript_biotype,
                    "representative_status": asite.representative_status,
                    "cluster_start": asite.cluster_start,
                    "cluster_end": asite.cluster_end,
                    "pa_level": asite.pa_level,
                    "sample_details": sample_details,
                }
            )

        transcript_data.append(
            {
                "transcript_id": transcript.transcript_id,
                "apa_site_count": len(apa_sites),
                "samples": _dedupe_sample_names(
                    sorted(sample_names, key=lambda value: _format_sample_name(value).lower())
                ),
                "apa_sites": transcript_apa_sites,
            }
        )

    return GeneDetail(
        id=gene.id,
        gene_id=gene.gene_id,
        gene_name=gene.gene_name,
        chromosome=gene.chromosome,
        strand=gene.strand,
        species=species_name,
        transcripts=transcript_data,
    )


@router.get("/gene/{gene_db_id}/summary")
def get_gene_summary(
    gene_db_id: int,
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Fetch species-aware gene summary from MyGene.info."""
    gene_query = db.query(Gene).filter(Gene.id == gene_db_id)
    if species:
        gene_query = gene_query.join(Species, Gene.species_id == Species.id).filter(
            Species.name == species
        )
    gene = gene_query.first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    species_obj = db.query(Species).filter(Species.id == gene.species_id).first()
    taxid = (
        str(species_obj.tax_id)
        if species_obj and species_obj.tax_id
        else _resolve_species_taxid(
            species_obj.name if species_obj else species,
            species_obj.latin_name if species_obj else None,
        )
    )
    if not taxid:
        return {
            "taxid": None,
            "summary": None,
            "source": "MyGene.info",
            "message": "No NCBI taxonomy ID was found for this species.",
        }

    cache_key = (gene.gene_name, taxid)
    if cache_key in _GENE_SUMMARY_CACHE:
        return _GENE_SUMMARY_CACHE[cache_key]

    params = urlencode(
        {
            "q": f"symbol:{gene.gene_name}",
            "fields": "name,summary,pathway.kegg,uniprot,entrezgene,HGNC,symbol,alias,type_of_gene,refseq,ensembl,taxid",
            "species": taxid,
            "size": "1",
        }
    )
    try:
        data = _http_json(f"https://mygene.info/v3/query?{params}")
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(status_code=502, detail="Gene summary lookup failed")

    hit = (data.get("hits") or [None])[0]
    if not hit:
        result = {
            "taxid": taxid,
            "summary": None,
            "source": "MyGene.info",
            "message": "No species-specific gene summary found.",
        }
        _GENE_SUMMARY_CACHE[cache_key] = result
        return result

    uniprot_raw = (hit.get("uniprot") or {}).get("Swiss-Prot")
    refseq_rna = (hit.get("refseq") or {}).get("rna") or []
    refseq_rna = refseq_rna if isinstance(refseq_rna, list) else [refseq_rna]
    pathways = (hit.get("pathway") or {}).get("kegg") or []
    pathways = pathways if isinstance(pathways, list) else [pathways]
    aliases = hit.get("alias") or []
    aliases = aliases if isinstance(aliases, list) else [aliases]
    ensembl = hit.get("ensembl") or {}

    result = {
        "taxid": taxid,
        "symbol": hit.get("symbol"),
        "fullName": hit.get("name"),
        "aliases": aliases,
        "geneType": hit.get("type_of_gene"),
        "summary": hit.get("summary"),
        "pathways": pathways,
        "entrezgene": hit.get("entrezgene"),
        "uniprot": _first_value(uniprot_raw),
        "hgnc": hit.get("HGNC"),
        "refseqMrna": next((rna for rna in refseq_rna if str(rna).startswith("NM_")), _first_value(refseq_rna)),
        "ensemblGene": ensembl.get("gene") if isinstance(ensembl, dict) else None,
        "source": "MyGene.info",
    }
    _GENE_SUMMARY_CACHE[cache_key] = result
    return result


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=1),
    field: str = Query("gene_name"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Autocomplete search suggestions."""
    term = q.strip()
    lower_term = term.lower()

    def match_rank(column):
        return case(
            (func.lower(column) == lower_term, 0),
            (func.lower(column).like(f"{lower_term}%"), 1),
            else_=2,
        )

    if field == "gene_name":
        results = (
            db.query(Gene.gene_name)
            .filter(Gene.gene_name.ilike(f"%{term}%"))
            .group_by(Gene.gene_name)
            .order_by(match_rank(Gene.gene_name), func.lower(Gene.gene_name))
            .limit(limit)
            .all()
        )
        return [{"value": r[0], "type": "gene_name"} for r in results]
    elif field == "gene_id":
        results = (
            db.query(Gene.gene_id)
            .filter(Gene.gene_id.ilike(f"%{term}%"))
            .group_by(Gene.gene_id)
            .order_by(match_rank(Gene.gene_id), func.lower(Gene.gene_id))
            .limit(limit)
            .all()
        )
        return [{"value": r[0], "type": "gene_id"} for r in results]
    elif field == "transcript_id":
        results = (
            db.query(Transcript.transcript_id)
            .filter(Transcript.transcript_id.ilike(f"%{term}%"))
            .group_by(Transcript.transcript_id)
            .order_by(match_rank(Transcript.transcript_id), func.lower(Transcript.transcript_id))
            .limit(limit)
            .all()
        )
        return [{"value": r[0], "type": "transcript_id"} for r in results]
    elif field == "sample":
        results = (
            db.query(Sample.name)
            .filter(Sample.name.ilike(f"%{term}%"))
            .group_by(Sample.name)
            .order_by(match_rank(Sample.name), func.lower(Sample.name))
            .limit(limit)
            .all()
        )
        return [{"value": r[0], "type": "sample"} for r in results]
    elif field == "species":
        results = _ranked_species_matches(db, term)[:limit]
        return [
            {
                "value": species_name,
                "type": "species",
                "display_name": _format_species_name(species_name, latin_name),
                "latin_name": latin_name,
                "aliases": species_aliases(species_name, latin_name),
            }
            for _, _, species_name, latin_name in results
        ]
    return []

@router.get("/transcript/{transcript_id}/structure")
def get_transcript_structure(
    transcript_id: str,
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    transcript = _query_transcript_by_public_id(db, transcript_id, species)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    gene = db.query(Gene).filter(Gene.id == transcript.gene_id).first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    apa_site_species = (
        db.query(APASite.species_id)
        .filter(APASite.transcript_id == transcript.id)
        .first()
    )
    if apa_site_species:
        species_obj = (
            db.query(Species).filter(Species.id == apa_site_species[0]).first()
        )
    else:
        species_obj = db.query(Species).filter(Species.name == "Human").first()

    if not species_obj:
        raise HTTPException(status_code=404, detail="Species not found")

    bed12_path = get_species_ref_path(species_obj.name, "bed12")
    if not bed12_path:
        raise HTTPException(
            status_code=404, detail="BED12 file not available for this species"
        )

    try:
        rec = _fetch_bed12_record(bed12_path, transcript_id)
        if not rec:
            raise HTTPException(
                status_code=404, detail="Transcript not found in BED12 index"
            )
        structure = _parse_bed12_structure(rec)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse BED12: {str(e)}")

    return {
        "transcript_id": transcript_id,
        "gene_name": gene.gene_name,
        "gene_id": gene.gene_id,
        "chromosome": structure["chrom"] or gene.chromosome,
        "strand": structure["strand"] or gene.strand,
        "exons": [{"start": s, "end": e} for s, e in structure["exons"]],
        "cds": [{"start": s, "end": e} for s, e in structure["cds"]],
        "utrs": [{"start": s, "end": e} for s, e in structure["utrs"]],
    }


@router.get("/transcript/{transcript_id}", response_model=LocusDetail)
def get_locus_detail(
    transcript_id: str,
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get detailed information about a transcript and its APA sites."""
    transcript = _query_transcript_by_public_id(db, transcript_id, species)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    gene = db.query(Gene).filter(Gene.id == transcript.gene_id).first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    apa_sites = db.query(APASite).filter(APASite.transcript_id == transcript.id).all()
    sample_details_by_site = _sample_detail_rows(db, [site.id for site in apa_sites])

    sample_names = set()
    apa_sites_with_details = []
    for asite in apa_sites:
        species_obj = db.query(Species).filter(Species.id == asite.species_id).first()

        sample_details = _dedupe_sample_details(sample_details_by_site.get(asite.id, []))
        for sd in sample_details:
            sample_names.add(sd.get("sample_name", ""))

        apa_sites_with_details.append(
            APASiteWithDetails(
                unified_id=str(asite.unified_id),
                transcript_id=int(asite.transcript_id),
                species_id=int(asite.species_id),
                mode_site_position=int(asite.mode_site_position),
                transcript_biotype=asite.transcript_biotype,
                representative_status=asite.representative_status,
                site_count=int(asite.site_count),
                site_abundance=float(asite.site_abundance),
                sample_data=json.dumps(sample_details),
                cluster_start=asite.cluster_start,
                cluster_end=asite.cluster_end,
                sequence=asite.sequence,
                pas_motif=asite.pas_motif,
                pas_position=asite.pas_position,
                pas_type=asite.pas_type,
                search_level=asite.search_level,
                pa_level=asite.pa_level,
                id=int(asite.id),
                transcript=transcript,
                species=species_obj,
                sample_details=sample_details,
            )
        )

    site_species_id = apa_sites[0].species_id if apa_sites else None
    sample_type_query = db.query(Sample)
    if sample_names:
        sample_type_query = sample_type_query.filter(Sample.name.in_(sample_names))
    if site_species_id:
        sample_type_query = sample_type_query.filter(Sample.species_id == site_species_id)
    sample_type_map = {
        sample.name: sample.sample_type for sample in sample_type_query.all()
    } if sample_names else {}
    deduped_sample_names = _dedupe_sample_names(
        sorted(sample_names, key=lambda value: _format_sample_name(value).lower())
    )
    samples = [
        {"name": name, "sample_type": sample_type_map.get(name, "cell_culture")}
        for name in deduped_sample_names
        if name
    ]
    chromosomes = [gene.chromosome] if gene.chromosome else []

    return LocusDetail(
        gene=gene,
        transcript=transcript,
        apa_sites=apa_sites_with_details,
        samples=samples,
        chromosomes=chromosomes,
    )


@router.get("/species")
def get_species(db: Session = Depends(get_db)):
    """Get all species."""
    species = db.query(Species).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "display_name": _format_species_name(s.name, s.latin_name),
            "latin_name": _format_sample_name(s.latin_name),
            "assembly": s.assembly,
            "tax_id": s.tax_id,
            "aliases": species_aliases(s.name, s.latin_name),
        }
        for s in species
    ]


@router.get("/samples")
def get_samples(species: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all samples (cell lines/tissues), optionally filtered by species."""
    query = db.query(Sample).join(Species)
    if species:
        query = query.filter(Species.name == species)
    samples = query.distinct().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "display_name": _format_sample_name(s.name),
            "species": s.species.name,
            "species_display_name": _format_species_name(
                s.species.name, s.species.latin_name
            ),
        }
        for s in samples
    ]


@router.get("/stats/detailed")
def get_detailed_stats(db: Session = Depends(get_db)):
    """Get detailed database statistics from the precomputed cache."""
    return _load_stats_cache()["detailed"]


@router.get("/stats/multiplicity")
def get_multiplicity_stats(
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get PA site multiplicity per transcript, optionally scoped to one species."""
    return _build_multiplicity_stats(db, species)


@router.get("/stats/pas-motifs")
def get_pas_motif_stats(
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get PAS motif distribution, optionally scoped to one species."""
    cached = _cached_pas_motif_stats(species)
    if cached is not None:
        return cached
    return _build_pas_motif_stats(db, species)


@router.get("/stats/pas-evidence")
def get_pas_evidence_stats(
    species: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    """Count unique PAS clusters by evidence level with species-specific context."""
    species_obj = db.query(Species).filter(Species.name == species).first()
    if species_obj is None:
        raise HTTPException(status_code=404, detail="Species not found")
    cached = _load_stats_cache().get("detailed", {}).get("pas_evidence_by_species", {})
    if species_obj.name in cached:
        return cached[species_obj.name]
    return build_pas_evidence_summary(db, species_obj)


@router.get("/stats/top-genes")
def get_top_gene_stats(
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get top genes by distinct PA site count, optionally scoped to one species."""
    return _build_top_gene_stats(db, species)


@router.get("/download/apa-sites")
def download_apa_sites(
    species: Optional[str] = None,
    sample: Optional[List[str]] = Query(None),
    gene_name: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|tsv|txt)$"),
    db: Session = Depends(get_db),
):
    """Download PA site observations in sample-resolved format."""
    selected_samples = [s for s in (sample or []) if s]
    delimiter = "," if format == "csv" else "\t"
    output = io.StringIO()

    headers = [
        "gene_name",
        "gene_id",
        "transcript_id",
        "site_id",
        "cluster_range",
        "representative_position",
        "sample_site_position",
        "site_abundance",
        "species",
        "sample",
    ]
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
    writer.writeheader()

    query = (
        db.query(
            Gene.gene_name,
            Gene.gene_id,
            Transcript.transcript_id,
            APASite.unified_id,
            APASite.cluster_start,
            APASite.cluster_end,
            APASite.mode_site_position,
            Species.name.label("species"),
            Sample.name.label("sample_name"),
            Sample.sample_type,
            APASiteSample.sample_order,
            APASiteSample.original_site_position,
            APASiteSample.site_abundance.label("sample_site_abundance"),
        )
        .select_from(Gene)
        .join(Transcript, Gene.id == Transcript.gene_id)
        .join(APASite, Transcript.id == APASite.transcript_id)
        .join(APASiteSample, APASiteSample.apa_site_id == APASite.id)
        .join(Sample, APASiteSample.sample_id == Sample.id)
        .join(Species, APASite.species_id == Species.id)
    )
    if species:
        query = query.filter(Species.name.ilike(f"%{species}%"))
    if gene_name:
        query = query.filter(Gene.gene_name.ilike(f"%{gene_name}%"))
    if selected_samples:
        query = query.filter(Sample.name.in_(selected_samples))

    query = query.order_by(
        Transcript.transcript_id,
        APASite.unified_id,
        APASiteSample.sample_order,
    )

    for row in query.yield_per(5000):
        _write_apa_site_download_row(
            writer,
            row,
            {
                "sample_name": row.sample_name,
                "sample_type": row.sample_type,
                "original_site_position": row.original_site_position,
                "site_abundance": row.sample_site_abundance,
            },
            selected_samples,
        )

    output.seek(0)
    media_type = "text/csv" if format == "csv" else "text/tab-separated-values"
    filename = f"apa_sites.{format}"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/genes")
def download_genes(
    species: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|tsv|txt)$"),
    db: Session = Depends(get_db),
):
    """Download genes data."""
    query = (
        db.query(
            Gene.gene_name,
            Gene.gene_id,
            Gene.chromosome,
            Gene.strand,
            Species.name.label("species"),
            func.count(Transcript.id).label("transcript_count"),
            func.count(APASite.id).label("apa_site_count"),
        )
        .join(Species, Gene.species_id == Species.id)
        .outerjoin(Transcript, Transcript.gene_id == Gene.id)
        .outerjoin(APASite, APASite.transcript_id == Transcript.id)
        .group_by(
            Gene.gene_name, Gene.gene_id, Gene.chromosome, Gene.strand, Species.name
        )
    )

    if species:
        query = query.filter(Species.name.ilike(f"%{species}%"))

    results = query.all()

    delimiter = "," if format == "csv" else "\t"
    output = io.StringIO()

    headers = [
        "gene_name",
        "gene_id",
        "chromosome",
        "strand",
        "species",
        "transcript_count",
        "apa_site_count",
    ]
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
    writer.writeheader()

    for row in results:
        writer.writerow(
            {
                "gene_name": row.gene_name or "",
                "gene_id": row.gene_id or "",
                "chromosome": row.chromosome or "",
                "strand": row.strand or "",
                "species": _format_species_name(row.species),
                "transcript_count": row.transcript_count or 0,
                "apa_site_count": row.apa_site_count or 0,
            }
        )

    output.seek(0)

    media_type = "text/csv" if format == "csv" else "text/tab-separated-values"
    filename = f"genes.{format}"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/transcripts")
def download_transcripts(
    species: Optional[str] = None,
    format: str = Query("csv", pattern="^(csv|tsv|txt)$"),
    db: Session = Depends(get_db),
):
    """Download transcripts data."""
    query = (
        db.query(
            Gene.gene_name,
            Gene.gene_id,
            Transcript.transcript_id,
            Gene.chromosome,
            Gene.strand,
            Species.name.label("species"),
            func.count(APASite.id).label("apa_site_count"),
        )
        .join(Gene, Transcript.gene_id == Gene.id)
        .join(Species, Transcript.species_id == Species.id)
        .outerjoin(APASite, APASite.transcript_id == Transcript.id)
        .group_by(
            Gene.gene_name,
            Gene.gene_id,
            Transcript.transcript_id,
            Gene.chromosome,
            Gene.strand,
            Species.name,
        )
    )

    if species:
        query = query.filter(Species.name.ilike(f"%{species}%"))

    results = query.all()

    delimiter = "," if format == "csv" else "\t"
    output = io.StringIO()

    headers = [
        "gene_name",
        "gene_id",
        "transcript_id",
        "chromosome",
        "strand",
        "species",
        "apa_site_count",
    ]
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
    writer.writeheader()

    for row in results:
        writer.writerow(
            {
                "gene_name": row.gene_name or "",
                "gene_id": row.gene_id or "",
                "transcript_id": row.transcript_id or "",
                "chromosome": row.chromosome or "",
                "strand": row.strand or "",
                "species": _format_species_name(row.species),
                "apa_site_count": row.apa_site_count or 0,
            }
        )

    output.seek(0)

    media_type = "text/csv" if format == "csv" else "text/tab-separated-values"
    filename = f"transcripts.{format}"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/bed")
def download_bed(
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Download PA sites as BED6 format for genome browser visualization (IGV, UCSC, JBrowse)."""
    query = (
        db.query(
            Gene.chromosome,
            APASite.mode_site_position,
            APASite.unified_id,
            Gene.strand,
        )
        .select_from(APASite)
        .join(Transcript, APASite.transcript_id == Transcript.id)
        .join(Gene, Transcript.gene_id == Gene.id)
        .join(Species, APASite.species_id == Species.id)
    )

    if species:
        query = query.filter(Species.name.ilike(f"%{species}%"))

    results = query.all()

    output = io.StringIO()
    output.write(
        'track name="IsoAPA_PA_Sites" description="IsoAPA Polyadenylation Sites" useScore=0\n'
    )

    for row in results:
        chrom = row.chromosome or "chrUnknown"
        site_pos = int(row.mode_site_position) if row.mode_site_position else 0
        chrom_start = max(0, site_pos - 1)  # BED is 0-based
        chrom_end = site_pos               # half-open end
        name = row.unified_id or "."
        strand = row.strand or "."
        output.write(f"{chrom}\t{chrom_start}\t{chrom_end}\t{name}\t.\t{strand}\n")

    output.seek(0)
    sp_suffix = f"_{_download_filename(species.lower().replace(' ', '_'))}" if species else ""
    filename = _download_filename(f"isoapa_pa_sites{sp_suffix}.bed")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/download/abundance-matrix")
def download_abundance_matrix(
    species: Optional[str] = None,
    sample: Optional[List[str]] = Query(None),
    format: str = Query("tsv", pattern="^(csv|tsv)$"),
    db: Session = Depends(get_db),
):
    """Download PA site × sample abundance matrix for differential APA analysis."""
    delimiter = "," if format == "csv" else "\t"
    selected_samples = sorted({s for s in (sample or []) if s})
    sample_query = db.query(Sample.name).join(Species)
    if species:
        sample_query = sample_query.filter(Species.name.ilike(f"%{species}%"))
    if selected_samples:
        sample_query = sample_query.filter(Sample.name.in_(selected_samples))
    sample_names = _dedupe_sample_names(
        sorted({row[0] for row in sample_query.all()}, key=lambda value: _format_sample_name(value).lower())
    )

    query = (
        db.query(
            APASite.unified_id,
            Transcript.transcript_id,
            Gene.gene_name,
            Gene.chromosome,
            Gene.strand,
            APASite.mode_site_position,
            APASite.id.label("apa_site_id"),
            Species.name.label("species"),
        )
        .select_from(APASite)
        .join(Transcript, APASite.transcript_id == Transcript.id)
        .join(Gene, Transcript.gene_id == Gene.id)
        .join(Species, APASite.species_id == Species.id)
    )

    if species:
        query = query.filter(Species.name.ilike(f"%{species}%"))
    if selected_samples:
        sample_filter = _sample_site_filter(db, selected_samples)
        if sample_filter is not None:
            query = query.filter(sample_filter)

    results = query.all()
    sample_details_by_site = _sample_detail_rows(db, [row.apa_site_id for row in results])

    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    display_sample_names = [_format_sample_name(s) for s in sample_names]
    sample_value_cols = [
        col
        for display_name in display_sample_names
        for col in (f"{display_name}_count", f"{display_name}_relative_abundance")
    ]
    header_cols = [
        "site_id", "transcript_id", "gene_name",
        "chromosome", "strand", "species",
    ] + sample_value_cols
    writer.writerow(header_cols)

    for row in results:
        sample_values: dict = {
            _sample_display_key(s): {"count": 0, "relative_abundance": 0}
            for s in sample_names
        }
        for sd in sample_details_by_site.get(row.apa_site_id, []):
            sname = sd.get("sample_name", "")
            sample_key = _sample_display_key(sname)
            if sample_key in sample_values:
                sample_values[sample_key]["count"] += int(sd.get("site_count", 0) or 0)
                sample_values[sample_key]["relative_abundance"] = sd.get("site_abundance", 0) or 0

        row_vals = [
            row.unified_id or "",
            row.transcript_id or "",
            row.gene_name or "",
            row.chromosome or "",
            row.strand or "",
            _format_species_name(row.species),
        ] + [
            str(value)
            for s in sample_names
            for sample_key in [_sample_display_key(s)]
            for value in (
                sample_values[sample_key]["count"],
                sample_values[sample_key]["relative_abundance"],
            )
        ]
        writer.writerow(row_vals)

    output.seek(0)
    sp_suffix = f"_{_download_filename(species.lower().replace(' ', '_'))}" if species else ""
    extension = "csv" if format == "csv" else "tsv"
    filename = _download_filename(f"isoapa_abundance_matrix{sp_suffix}.{extension}")
    media_type = "text/csv" if format == "csv" else "text/tab-separated-values"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# FASTA index cache
# ---------------------------------------------------------------------------
_FASTA_INDEX_CACHE: dict = {}  # fasta_path -> dict of chrom entries


def _load_fasta_index(fasta_path: str) -> dict:
    if fasta_path in _FASTA_INDEX_CACHE:
        return _FASTA_INDEX_CACHE[fasta_path]
    idx_path = fasta_path + ".fidx"
    if not os.path.exists(idx_path):
        return {}
    with open(idx_path) as fh:
        idx = json.load(fh)
    _FASTA_INDEX_CACHE[fasta_path] = idx
    return idx


def _fetch_fasta_seq(fasta_path: str, chrom: str, start: int, end: int) -> str:
    """Return sequence [start, end) (0-based half-open) for chrom. Returns '' on failure."""
    idx = _load_fasta_index(fasta_path)
    # Accept both 'chr1' and '1' style chroms
    entry = idx.get(chrom) or idx.get(chrom.lstrip("chr")) or idx.get("chr" + chrom)
    if not entry:
        return ""
    offset = entry["offset"]
    line_len = entry["line_len"]
    line_bytes = entry["line_bytes"]

    if start < 0:
        start = 0
    if end <= start:
        return ""

    lines_before_start = start // line_len
    byte_start = offset + lines_before_start * line_bytes + (start % line_len)

    lines_before_end = (end - 1) // line_len
    byte_end = offset + lines_before_end * line_bytes + ((end - 1) % line_len) + 1

    with open(fasta_path, "rb") as fh:
        fh.seek(byte_start)
        raw = fh.read(byte_end - byte_start)

    seq = (
        raw.replace(b"\n", b"")
        .replace(b"\r", b"")
        .decode("ascii", errors="replace")
        .upper()
    )
    return seq[: end - start]


# ---------------------------------------------------------------------------
# ±50 bp sequence context around a PA site cleavage position
# ---------------------------------------------------------------------------


@router.get("/transcript/{transcript_id}/site-sequence/{site_id}")
def get_site_sequence_context(
    transcript_id: str,
    site_id: str,
    species: Optional[str] = None,
    db: Session = Depends(get_db),
):
    transcript = _query_transcript_by_public_id(db, transcript_id, species)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    gene = db.query(Gene).filter(Gene.id == transcript.gene_id).first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    apa_site = (
        db.query(APASite)
        .filter(APASite.transcript_id == transcript.id, APASite.unified_id == site_id)
        .first()
    )
    if not apa_site:
        raise HTTPException(status_code=404, detail="APA site not found")

    seq = apa_site.sequence or ""
    cleavage_index = len(seq) // 2 if seq else 50

    return {
        "unified_id": site_id,
        "mode_site_position": int(apa_site.mode_site_position),
        "chromosome": str(gene.chromosome),
        "strand": str(gene.strand),
        "flank": (len(seq) - 1) // 2 if seq else 50,
        "sequence": seq,
        "cleavage_index": cleavage_index,
        "pas_motif": apa_site.pas_motif,
        "pas_position": apa_site.pas_position,
        "pas_type": apa_site.pas_type,
    }
